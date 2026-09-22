from __future__ import annotations

import hashlib
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from sweagent import REPO_ROOT
from sweagent.requirements.models import RequirementsConfig, RequirementRecord
from sweagent.requirements.store import RequirementStore
from sweagent.requirements.wecom import WeComClient, extract_requirement
from sweagent.utils.config import load_environment_variables


def load_requirements_config(path: Path | str) -> RequirementsConfig:
    config_path = Path(path)
    if not config_path.is_absolute():
        config_path = REPO_ROOT / config_path
    data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    config = RequirementsConfig.model_validate(data)
    env_path = Path(config.env_file)
    if not env_path.is_absolute():
        env_path = REPO_ROOT / env_path
    if env_path.exists():
        load_environment_variables(env_path)
    return config


def _resolve_repo_path(path: str) -> Path:
    value = Path(path)
    return value if value.is_absolute() else (REPO_ROOT / value).resolve()


class RequirementWorkflow:
    def __init__(self, config_path: Path | str = "config/requirements.yaml"):
        self.config = load_requirements_config(config_path)
        self.client = WeComClient(self.config.wecom)
        self.store = RequirementStore(_resolve_repo_path(self.config.workflow.state_file))

    def inspect(self, approval_id: str) -> tuple[dict[str, Any], RequirementRecord]:
        detail = self.client.get_approval_detail(approval_id)
        record = extract_requirement(detail, approval_id=approval_id, config=self.config.approval)
        return detail, record

    def sync(self, approval_id: str, *, dry_run: bool = False) -> RequirementRecord:
        _, record = self.inspect(approval_id)
        if (
            self.config.approval.require_approved
            and record.approval_status not in self.config.approval.approved_statuses
        ):
            msg = (
                f"审批 {approval_id} 状态为 {record.approval_status}，"
                f"不在已通过状态 {self.config.approval.approved_statuses} 中"
            )
            raise ValueError(msg)
        if not dry_run:
            self.client.send_group_text(record.notification_text)
            record.notified_at = datetime.now()
            record.status = "notified"
        record.updated_at = datetime.now()
        self.store.put(record)
        return record

    def _problem_text(self, record: RequirementRecord) -> str:
        return (
            "# 企业微信需求申请\n\n"
            f"- 审批编号: {record.approval_id}\n"
            f"- 申请日期: {record.approval_date}\n"
            f"- 需求标题: {record.title or '(未提供)'}\n\n"
            "## 需求内容\n\n"
            f"{record.content}\n\n"
            "请按照 SWE2 原有流程分析本地仓库，进行最小范围修改，"
            "运行必要的验证命令，并提交最终补丁。不要修改与需求无关的文件。\n"
        )

    def _check_repository(self, repo_path: Path) -> None:
        if not repo_path.is_dir():
            msg = f"本地仓库路径不存在: {repo_path}"
            raise ValueError(msg)
        if self.config.repository.allow_dirty:
            return
        result = subprocess.run(
            ["git", "-C", str(repo_path), "status", "--porcelain"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            msg = f"无法检查 Git 仓库状态: {repo_path}\n{result.stderr}"
            raise ValueError(msg)
        if result.stdout.strip():
            msg = f"本地仓库有未提交修改，请先提交或 stash: {repo_path}"
            raise ValueError(msg)

    def run(self, approval_id: str, *, require_existing: bool = True) -> RequirementRecord:
        record = self.store.get(approval_id)
        if record is None:
            if require_existing:
                msg = f"状态文件中没有审批 {approval_id}，请先执行 sync"
                raise ValueError(msg)
            record = self.sync(approval_id)

        if not self.config.repository.path.strip():
            msg = "请先配置 repository.path 为需要修改的本地 Git 仓库"
            raise ValueError(msg)

        repo_path = _resolve_repo_path(self.config.repository.path)
        self._check_repository(repo_path)

        problem_dir = _resolve_repo_path(self.config.workflow.problem_dir)
        problem_dir.mkdir(parents=True, exist_ok=True)
        problem_text = self._problem_text(record)
        problem_path = problem_dir / f"{approval_id}.md"
        problem_path.write_text(problem_text, encoding="utf-8")

        output_dir = _resolve_repo_path(self.config.repository.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        command = [sys.executable, "-m", "sweagent", "run"]
        for config_file in self.config.repository.swe_configs:
            resolved_config = _resolve_repo_path(config_file)
            command.extend(["--config", str(resolved_config)])
        command.extend(
            [
                f"--env.repo.path={repo_path}",
                f"--problem_statement.path={problem_path}",
                f"--output_dir={output_dir}",
            ]
        )
        if self.config.workflow.apply_patch_locally:
            command.append("--actions.apply_patch_locally=true")

        record.status = "running"
        record.problem_path = str(problem_path)
        record.run_output_dir = str(output_dir)
        record.updated_at = datetime.now()
        self.store.put(record)

        child_env = os.environ.copy()
        child_env.setdefault("PYTHONUTF8", "1")
        child_env.setdefault("PYTHONIOENCODING", "utf-8")
        try:
            subprocess.run(command, cwd=REPO_ROOT, check=True, env=child_env)
        except Exception as exc:
            record.status = "failed"
            record.last_error = str(exc)
            record.updated_at = datetime.now()
            self.store.put(record)
            raise

        problem_id = hashlib.sha256(problem_text.encode("utf-8")).hexdigest()[:6]
        patch_path = output_dir / problem_id / f"{problem_id}.patch"
        record.patch_path = str(patch_path) if patch_path.exists() else None
        record.status = "completed" if patch_path.exists() else "failed"
        if patch_path.exists():
            record.last_error = None
        else:
            record.last_error = f"SWE2 未生成预期补丁: {patch_path}"
        record.updated_at = datetime.now()
        self.store.put(record)
        return record

    def process(self, approval_id: str, *, dry_run: bool = False) -> RequirementRecord:
        record = self.sync(approval_id, dry_run=dry_run)
        if dry_run:
            return record
        return self.run(approval_id)

    def list_records(self) -> list[RequirementRecord]:
        return self.store.list()



