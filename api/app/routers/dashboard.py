from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.models.audit_log import AuditLog
from app.models.authorized_target import AuthorizedTarget
from app.models.scan_result import ScanResult, ScanStatus, ScanType
from app.models.siem_analysis import SiemAnalysis
from app.models.user import User
from app.schemas.dashboard import DashboardActivity, DashboardResponse

router = APIRouter(tags=["dashboard"])

SOURCE_PRIORITY = {"scan": 1, "audit": 2, "siem": 3}


@dataclass(frozen=True)
class _RankedActivity:
    activity: DashboardActivity
    source_id: int

    @property
    def sort_key(self) -> tuple[datetime, int, int]:
        return (
            self.activity.timestamp,
            SOURCE_PRIORITY[self.activity.type],
            self.source_id,
        )


def _scan_activity(scan: ScanResult, target: str) -> _RankedActivity:
    label = "Recon" if scan.type == ScanType.RECON else "Web Audit"
    return _RankedActivity(
        activity=DashboardActivity(
            type="scan",
            title=f"{label}: {target}",
            status=scan.status.value,
            timestamp=scan.updated_at,
        ),
        source_id=scan.id,
    )


def _audit_activity(log: AuditLog) -> _RankedActivity:
    return _RankedActivity(
        activity=DashboardActivity(
            type="audit",
            title=f"{log.method} {log.endpoint}",
            status="success" if log.status_code < 400 else "error",
            timestamp=log.timestamp,
        ),
        source_id=log.id,
    )


def _siem_activity(
    analysis_id: int, source: str, summary: dict, timestamp: datetime
) -> _RankedActivity:
    return _RankedActivity(
        activity=DashboardActivity(
            type="siem",
            title=f"SIEM: {source}",
            status="alert" if int(summary.get("detections", 0)) > 0 else "clear",
            timestamp=timestamp,
        ),
        source_id=analysis_id,
    )


@router.get("/dashboard", response_model=DashboardResponse)
def dashboard(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DashboardResponse:
    scans = db.scalar(
        select(func.count(ScanResult.id)).where(ScanResult.user_id == user.id)
    ) or 0
    web_score = db.scalar(
        select(func.avg(ScanResult.result["score"].as_float())).where(
            ScanResult.user_id == user.id,
            ScanResult.type == ScanType.WEBAUDIT,
            ScanResult.status == ScanStatus.COMPLETED,
            ScanResult.result.is_not(None),
        )
    )
    alerts = db.scalar(
        select(
            func.coalesce(
                func.sum(SiemAnalysis.summary["detections"].as_integer()), 0
            )
        ).where(SiemAnalysis.user_id == user.id)
    ) or 0

    scan_rows = db.execute(
        select(ScanResult, AuthorizedTarget.target)
        .join(
            AuthorizedTarget,
            (AuthorizedTarget.id == ScanResult.target_id)
            & (AuthorizedTarget.user_id == ScanResult.user_id),
        )
        .where(ScanResult.user_id == user.id)
        .order_by(ScanResult.updated_at.desc(), ScanResult.id.desc())
        .limit(3)
    ).all()
    audit_logs = db.scalars(
        select(AuditLog)
        .where(AuditLog.user_id == user.id)
        .order_by(AuditLog.timestamp.desc(), AuditLog.id.desc())
        .limit(3)
    ).all()
    analyses = db.execute(
        select(
            SiemAnalysis.id,
            SiemAnalysis.source,
            SiemAnalysis.summary,
            SiemAnalysis.timestamp,
        )
        .where(SiemAnalysis.user_id == user.id)
        .order_by(SiemAnalysis.timestamp.desc(), SiemAnalysis.id.desc())
        .limit(3)
    ).all()

    activities: list[_RankedActivity] = [
        *(_scan_activity(scan, target) for scan, target in scan_rows),
        *(_audit_activity(log) for log in audit_logs),
        *(_siem_activity(*analysis) for analysis in analyses),
    ]
    activities.sort(key=lambda item: item.sort_key, reverse=True)

    return DashboardResponse(
        scans=scans,
        web_score=round(float(web_score), 2) if web_score is not None else None,
        alerts=int(alerts),
        recent_activity=[item.activity for item in activities[:3]],
    )
