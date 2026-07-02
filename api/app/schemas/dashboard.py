from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class DashboardActivity(BaseModel):
    type: Literal["scan", "audit", "siem"]
    title: str
    status: str
    timestamp: datetime


class DashboardResponse(BaseModel):
    scans: int
    web_score: float | None
    alerts: int
    recent_activity: list[DashboardActivity]
