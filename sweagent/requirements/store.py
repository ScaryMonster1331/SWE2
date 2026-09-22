from __future__ import annotations

import json
from pathlib import Path

from sweagent.requirements.models import RequirementRecord


class RequirementStore:
    """使用单个 JSON 文件保存企业微信需求处理状态。"""

    def __init__(self, path: Path | str):
        self.path = Path(path)
        self._records: dict[str, RequirementRecord] = {}
        self.load()

    def load(self) -> None:
        if not self.path.exists():
            self._records = {}
            return
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        self._records = {
            approval_id: RequirementRecord.model_validate(record)
            for approval_id, record in raw.items()
        }

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            approval_id: record.model_dump(mode="json")
            for approval_id, record in sorted(self._records.items())
        }
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(self.path)

    def get(self, approval_id: str) -> RequirementRecord | None:
        return self._records.get(approval_id)

    def put(self, record: RequirementRecord) -> None:
        self._records[record.approval_id] = record
        self.save()

    def list(self) -> list[RequirementRecord]:
        return sorted(self._records.values(), key=lambda item: item.created_at)
