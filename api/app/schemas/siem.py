from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class SiemAnalysisResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source: str
    summary: dict[str, Any]
    events: list[dict[str, Any]]
    timestamp: datetime


class AuditActivityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    endpoint: str
    method: str
    source_ip: str
    status_code: int
    timestamp: datetime


class SiemDashboardResponse(BaseModel):
    analyses: list[SiemAnalysisResponse]
    recent_activity: list[AuditActivityResponse]
