from __future__ import annotations

import os
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class WeComConfig(BaseModel):
    """企业微信 API 与群机器人配置。密钥本身只从环境变量读取。"""

    base_url: str = "https://qyapi.weixin.qq.com/cgi-bin"
    corp_id_env: str = "WECOM_CORP_ID"
    corp_secret_env: str = "WECOM_CORP_SECRET"
    webhook_key_env: str = "WECOM_WEBHOOK_KEY"
    notification_group: str = "需求通知"
    request_timeout: float = 20.0
    max_text_bytes: int = 1900

    model_config = ConfigDict(extra="forbid")

    @property
    def corp_id(self) -> str:
        return os.getenv(self.corp_id_env, "").strip()

    @property
    def corp_secret(self) -> str:
        return os.getenv(self.corp_secret_env, "").strip()

    @property
    def webhook_key(self) -> str:
        return os.getenv(self.webhook_key_env, "").strip()

    def validate_credentials(self) -> None:
        missing = []
        if not self.corp_id:
            missing.append(self.corp_id_env)
        if not self.corp_secret:
            missing.append(self.corp_secret_env)
        if not self.webhook_key:
            missing.append(self.webhook_key_env)
        if missing:
            msg = "缺少企业微信环境变量: " + ", ".join(missing)
            raise ValueError(msg)


class ApprovalConfig(BaseModel):
    require_approved: bool = True
    approved_statuses: list[int] = Field(default_factory=lambda: [2])
    date_source: Literal["approval", "today"] = "approval"
    include_title: bool = True
    title_field_names: list[str] = Field(
        default_factory=lambda: ["需求标题", "标题", "title", "sp_name"]
    )
    content_field_names: list[str] = Field(
        default_factory=lambda: ["需求内容", "需求描述", "内容", "description"]
    )

    model_config = ConfigDict(extra="forbid")


class RepositoryConfig(BaseModel):
    path: str = ""
    base_commit: str = "HEAD"
    swe_configs: list[str] = Field(
        default_factory=lambda: ["config/default.yaml", "config/deepseek_flash.yaml"]
    )
    output_dir: str = "requirements/runs"
    allow_dirty: bool = False

    model_config = ConfigDict(extra="forbid")


class WorkflowConfig(BaseModel):
    state_file: str = "requirements/state.json"
    problem_dir: str = "requirements/problem_statements"
    notify_before_run: bool = True
    apply_patch_locally: bool = False

    model_config = ConfigDict(extra="forbid")


class RequirementsConfig(BaseModel):
    env_file: str = ".env"
    wecom: WeComConfig = Field(default_factory=WeComConfig)
    approval: ApprovalConfig = Field(default_factory=ApprovalConfig)
    repository: RepositoryConfig = Field(default_factory=RepositoryConfig)
    workflow: WorkflowConfig = Field(default_factory=WorkflowConfig)

    model_config = ConfigDict(extra="forbid")


class ApprovalField(BaseModel):
    field_id: str = ""
    title: str = ""
    value: str = ""

    model_config = ConfigDict(extra="forbid")


class RequirementRecord(BaseModel):
    approval_id: str
    approval_status: int | None = None
    approval_date: str
    title: str = ""
    content: str
    notification_text: str
    status: Literal["discovered", "notified", "running", "completed", "failed"] = "discovered"
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    notified_at: datetime | None = None
    problem_path: str | None = None
    patch_path: str | None = None
    run_output_dir: str | None = None
    last_error: str | None = None

    model_config = ConfigDict(extra="forbid")
