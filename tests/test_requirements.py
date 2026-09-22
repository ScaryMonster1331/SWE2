from __future__ import annotations

from sweagent.requirements.models import ApprovalConfig, RequirementRecord
from sweagent.requirements.store import RequirementStore
from sweagent.requirements.wecom import extract_requirement


def test_extract_requirement_from_approval_detail():
    detail = {
        "info": {
            "sp_name": "示例审批",
            "sp_status": 2,
            "apply_time": 1789992000,
            "apply_data": {
                "contents": [
                    {"id": "title", "title": "需求标题", "value": "优化登录流程"},
                    {"id": "content", "title": "需求内容", "value": "增加登录失败提示，并补充单元测试。"},
                ]
            },
        }
    }

    record = extract_requirement(detail, approval_id="SP-001", config=ApprovalConfig())

    assert record.approval_id == "SP-001"
    assert record.approval_status == 2
    assert record.title == "优化登录流程"
    assert record.content == "优化登录流程\n增加登录失败提示，并补充单元测试。"
    assert record.notification_text.startswith("[")
    assert "优化登录流程" in record.notification_text


def test_extract_requirement_falls_back_to_all_values():
    detail = {
        "info": {
            "sp_status": 2,
            "apply_time": 1789992000,
            "apply_data": {
                "contents": [
                    {"id": "a", "title": "字段A", "value": "A"},
                    {"id": "b", "title": "字段B", "value": "B"},
                ]
            },
        }
    }

    record = extract_requirement(detail, approval_id="SP-002", config=ApprovalConfig())

    assert record.content == "A\nB"
    assert record.notification_text.endswith("A\nB")


def test_requirement_store_roundtrip(tmp_path):
    store_path = tmp_path / "requirements.json"
    store = RequirementStore(store_path)
    record = RequirementRecord(
        approval_id="SP-003",
        approval_status=2,
        approval_date="2026-09-22",
        title="标题",
        content="需求",
        notification_text="[2026-09-22] 需求",
    )

    store.put(record)
    loaded = RequirementStore(store_path).get("SP-003")

    assert loaded is not None
    assert loaded.approval_id == "SP-003"
    assert loaded.content == "需求"
