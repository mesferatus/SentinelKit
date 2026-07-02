from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict

from app.models import ScanStatus, ScanType


class TaskStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    task_id: str
    type: ScanType
    status: ScanStatus
    result: dict[str, Any] | list[Any] | None
    error: str | None
