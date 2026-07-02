from __future__ import annotations

from pathlib import PurePath

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.models.audit_log import AuditLog
from app.models.siem_analysis import SiemAnalysis
from app.models.user import User
from app.schemas.siem import SiemAnalysisResponse, SiemDashboardResponse
from app.services.siem_engine import LogEvent, analyze_events, parse_access_log

router = APIRouter(prefix="/siem", tags=["siem"])


def _safe_upload_text(file: UploadFile) -> str:
    data = file.file.read(settings.max_upload_bytes + 1)
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(status_code=413, detail="Arquivo excede o limite permitido")
    if b"\x00" in data:
        raise HTTPException(status_code=400, detail="Arquivo binário não permitido")
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise HTTPException(
            status_code=400, detail="Arquivo deve ser texto UTF-8"
        ) from exc


def _internal_events(db: Session, user_id: int) -> list[LogEvent]:
    logs = db.scalars(
        select(AuditLog)
        .where(AuditLog.user_id == user_id)
        .order_by(AuditLog.timestamp)
    ).all()
    return [
        LogEvent(
            ip=log.source_ip,
            timestamp=log.timestamp,
            method=log.method,
            path=log.endpoint,
            status=log.status_code,
        )
        for log in logs
    ]


@router.post(
    "/analyze",
    response_model=SiemAnalysisResponse,
    status_code=status.HTTP_201_CREATED,
)
def analyze(
    source: str = Form(...),
    file: UploadFile | None = File(default=None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if source == "internal":
        source_name = "internal_audit_logs"
        log_events = _internal_events(db, user.id)
    elif source == "upload":
        if file is None:
            raise HTTPException(status_code=422, detail="Arquivo de log obrigatório")
        text = _safe_upload_text(file)
        log_events = parse_access_log(text)
        source_name = PurePath(file.filename or "upload.log").name[:255]
    else:
        raise HTTPException(status_code=422, detail="Fonte de análise inválida")

    result = analyze_events(
        log_events,
        brute_force_threshold=settings.siem_brute_force_threshold,
        enumeration_threshold=settings.siem_enumeration_404_threshold,
        window_seconds=settings.siem_detection_window_seconds,
    )
    analysis = SiemAnalysis(
        user_id=user.id,
        source=source_name,
        summary=result.summary,
        events=result.events,
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)
    return analysis


@router.get("/dashboard", response_model=SiemDashboardResponse)
def dashboard(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    analyses = db.scalars(
        select(SiemAnalysis)
        .where(SiemAnalysis.user_id == user.id)
        .order_by(SiemAnalysis.timestamp.desc(), SiemAnalysis.id.desc())
        .limit(20)
    ).all()
    recent_activity = db.scalars(
        select(AuditLog)
        .where(AuditLog.user_id == user.id)
        .order_by(AuditLog.timestamp.desc(), AuditLog.id.desc())
        .limit(20)
    ).all()
    return {"analyses": analyses, "recent_activity": recent_activity}
