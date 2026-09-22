from __future__ import annotations

from collections.abc import Iterable
from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

import requests

from sweagent.requirements.models import (
    ApprovalConfig,
    ApprovalField,
    RequirementRecord,
    WeComConfig,
)


class WeComAPIError(RuntimeError):
    """企业微信 API 返回非零 errcode 时抛出。"""


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        return "\n".join(part for item in value if (part := _as_text(item)))
    if isinstance(value, dict):
        for key in ("text", "value", "content", "name"):
            if key in value:
                text = _as_text(value[key])
                if text:
                    return text
        return "\n".join(part for item in value.values() if (part := _as_text(item)))
    return str(value).strip()


def _iter_fields(value: Any) -> Iterable[ApprovalField]:
    if isinstance(value, dict):
        field_id = _as_text(value.get("id"))
        title = _as_text(value.get("title")) or _as_text(value.get("name"))
        field_value = _as_text(value.get("value"))
        if field_id or title:
            yield ApprovalField(field_id=field_id, title=title, value=field_value)
        for key in ("contents", "children"):
            child = value.get(key)
            if isinstance(child, (dict, list)):
                yield from _iter_fields(child)
    elif isinstance(value, list):
        for item in value:
            yield from _iter_fields(item)


def flatten_approval_fields(detail: dict[str, Any]) -> list[ApprovalField]:
    info = detail.get("info", detail)
    apply_data = info.get("apply_data", {}) if isinstance(info, dict) else {}
    fields = list(_iter_fields(apply_data))
    unique: dict[tuple[str, str], ApprovalField] = {}
    for field in fields:
        unique[(field.field_id, field.title)] = field
    return list(unique.values())


def _match_field(fields: list[ApprovalField], names: list[str]) -> ApprovalField | None:
    normalized = [name.strip().casefold() for name in names if name.strip()]
    for field in fields:
        if field.field_id.casefold() in normalized or field.title.casefold() in normalized:
            return field
    for field in fields:
        haystack = f"{field.field_id} {field.title}".casefold()
        if any(name in haystack for name in normalized):
            return field
    return None


def _approval_date(info: dict[str, Any], config: ApprovalConfig) -> str:
    if config.date_source == "today":
        return datetime.now(ZoneInfo("Asia/Shanghai")).date().isoformat()
    raw = info.get("apply_time") or info.get("create_time")
    try:
        timestamp = float(raw)
        if timestamp > 10_000_000_000:
            timestamp /= 1000
        return datetime.fromtimestamp(timestamp, ZoneInfo("Asia/Shanghai")).date().isoformat()
    except (TypeError, ValueError, OSError):
        return date.today().isoformat()


def extract_requirement(
    detail: dict[str, Any],
    *,
    approval_id: str,
    config: ApprovalConfig,
) -> RequirementRecord:
    info = detail.get("info", detail)
    fields = flatten_approval_fields(detail)

    title_field = _match_field(fields, config.title_field_names)
    content_field = _match_field(fields, config.content_field_names)
    title = title_field.value if title_field else _as_text(info.get("sp_name"))
    content = content_field.value if content_field else ""

    if not content:
        excluded = title_field
        content = "\n".join(field.value for field in fields if field != excluded and field.value)

    if config.include_title and title and title not in content:
        content = f"{title}\n{content}".strip()
    if not content:
        content = title or f"审批编号 {approval_id}"

    status_raw = info.get("sp_status")
    try:
        status = int(status_raw) if status_raw is not None else None
    except (TypeError, ValueError):
        status = None

    approval_date = _approval_date(info, config)
    notification_text = f"[{approval_date}] {content}"
    return RequirementRecord(
        approval_id=approval_id,
        approval_status=status,
        approval_date=approval_date,
        title=title,
        content=content,
        notification_text=notification_text,
    )


class WeComClient:
    def __init__(self, config: WeComConfig):
        self.config = config
        self._access_token: str | None = None
        self._access_token_expires_at = 0.0

    @staticmethod
    def _check_response(payload: dict[str, Any]) -> dict[str, Any]:
        errcode = int(payload.get("errcode", 0) or 0)
        if errcode != 0:
            msg = f"企业微信 API 错误 {errcode}: {payload.get('errmsg', 'unknown error')}"
            raise WeComAPIError(msg)
        return payload

    def access_token(self, *, force_refresh: bool = False) -> str:
        import time

        if not force_refresh and self._access_token and time.time() < self._access_token_expires_at:
            return self._access_token
        if not self.config.corp_id or not self.config.corp_secret:
            msg = f"缺少 {self.config.corp_id_env} 或 {self.config.corp_secret_env}"
            raise ValueError(msg)
        response = requests.get(
            f"{self.config.base_url}/gettoken",
            params={"corpid": self.config.corp_id, "corpsecret": self.config.corp_secret},
            timeout=self.config.request_timeout,
        )
        response.raise_for_status()
        payload = self._check_response(response.json())
        self._access_token = str(payload["access_token"])
        self._access_token_expires_at = time.time() + int(payload.get("expires_in", 7200)) - 60
        return self._access_token

    def get_approval_detail(self, approval_id: str) -> dict[str, Any]:
        if not approval_id.strip():
            msg = "审批编号不能为空"
            raise ValueError(msg)
        response = requests.post(
            f"{self.config.base_url}/oa/getapprovaldetail",
            params={"access_token": self.access_token()},
            json={"sp_no": approval_id.strip()},
            timeout=self.config.request_timeout,
        )
        response.raise_for_status()
        return self._check_response(response.json())

    def send_group_text(self, content: str) -> dict[str, Any]:
        if not self.config.webhook_key:
            msg = f"缺少 {self.config.webhook_key_env}"
            raise ValueError(msg)
        encoded = content.encode("utf-8")
        if len(encoded) > self.config.max_text_bytes:
            content = encoded[: self.config.max_text_bytes].decode("utf-8", errors="ignore") + "..."
        if self.config.webhook_key.startswith("http"):
            url = self.config.webhook_key
        else:
            url = f"{self.config.base_url}/webhook/send?key={self.config.webhook_key}"
        response = requests.post(
            url,
            json={"msgtype": "text", "text": {"content": content}},
            timeout=self.config.request_timeout,
        )
        response.raise_for_status()
        return self._check_response(response.json())

