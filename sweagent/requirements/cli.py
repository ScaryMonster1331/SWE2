from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from sweagent import REPO_ROOT
from sweagent.requirements.workflow import RequirementWorkflow


def _default_config() -> str:
    configured = REPO_ROOT / "config" / "requirements.yaml"
    if configured.exists():
        return str(configured)
    return str(REPO_ROOT / "config" / "requirements.example.yaml")


def _print_record(record) -> None:
    payload = record.model_dump(mode="json")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="企业微信审批需求与 SWE2 本地补丁流程")
    parser.add_argument("--config", default=_default_config(), help="需求工作流配置文件")
    subparsers = parser.add_subparsers(dest="command", required=True)

    inspect_parser = subparsers.add_parser("inspect", help="读取审批详情并展示解析结果")
    inspect_parser.add_argument("--approval-id", required=True, help="企业微信审批编号 sp_no")

    sync_parser = subparsers.add_parser("sync", help="读取审批并向需求通知群发送消息")
    sync_parser.add_argument("--approval-id", required=True, help="企业微信审批编号 sp_no")
    sync_parser.add_argument("--dry-run", action="store_true", help="只解析和保存，不发送群消息")

    run_parser = subparsers.add_parser("run", help="根据已同步需求运行原 SWE2 流程")
    run_parser.add_argument("--approval-id", required=True, help="企业微信审批编号 sp_no")
    run_parser.add_argument("--sync-if-missing", action="store_true", help="本地无记录时先同步审批")

    process_parser = subparsers.add_parser("process", help="同步通知后继续运行 SWE2")
    process_parser.add_argument("--approval-id", required=True, help="企业微信审批编号 sp_no")
    process_parser.add_argument("--dry-run", action="store_true", help="只执行审批解析，不发送和运行")

    subparsers.add_parser("list", help="列出已处理的需求")
    return parser


def run_from_cli(args: list[str] | None = None) -> int:
    parser = build_parser()
    parsed = parser.parse_args(args)
    workflow = RequirementWorkflow(Path(parsed.config))

    if parsed.command == "inspect":
        detail, record = workflow.inspect(parsed.approval_id)
        fields = detail.get("info", detail).get("apply_data", {}).get("contents", [])
        print(
            json.dumps(
                {
                    "approval_id": parsed.approval_id,
                    "approval_status": record.approval_status,
                    "approval_date": record.approval_date,
                    "title": record.title,
                    "content": record.content,
                    "notification_text": record.notification_text,
                    "raw_fields": fields,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    if parsed.command == "sync":
        return _print_record(workflow.sync(parsed.approval_id, dry_run=parsed.dry_run)) or 0

    if parsed.command == "run":
        return _print_record(
            workflow.run(parsed.approval_id, require_existing=not parsed.sync_if_missing)
        ) or 0

    if parsed.command == "process":
        return _print_record(workflow.process(parsed.approval_id, dry_run=parsed.dry_run)) or 0

    if parsed.command == "list":
        print(json.dumps([item.model_dump(mode="json") for item in workflow.list_records()], ensure_ascii=False, indent=2))
        return 0

    parser.error(f"Unknown command: {parsed.command}")
    return 2


def main(args: list[str] | None = None) -> None:
    try:
        raise SystemExit(run_from_cli(args))
    except Exception as exc:
        print(f"错误: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
