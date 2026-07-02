from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.rate_limit import authenticated_user_key, limiter
from app.dependencies.auth import get_current_user
from app.models import ScanResult, ScanStatus, ScanType, User
from app.schemas.webaudit import WebAuditCheckRequest, WebAuditCheckResponse
from app.services.target_service import validate_authorized_target
from app.services.web_auditor import URLValidationError, validate_webaudit_url
from app.tasks.webaudit import run_web_audit

router = APIRouter(prefix="/webaudit", tags=["webaudit"])


@router.post(
    "/check",
    response_model=WebAuditCheckResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
@limiter.limit(
    lambda: f"{settings.scan_tasks_per_user_per_hour}/hour",
    key_func=authenticated_user_key,
)
def create_web_audit(
    request: Request,
    payload: WebAuditCheckRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    target = validate_authorized_target(db, user, payload.target_id)
    try:
        validated_url = validate_webaudit_url(target.target, str(payload.url))
    except URLValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    scan = ScanResult(
        user_id=user.id,
        target_id=target.id,
        task_id=uuid4().hex,
        type=ScanType.WEBAUDIT,
        status=ScanStatus.PENDING,
    )
    db.add(scan)
    db.commit()
    db.refresh(scan)
    try:
        run_web_audit.delay(scan.id, validated_url)
    except Exception as exc:
        scan.status = ScanStatus.FAILED
        scan.error = "Não foi possível enfileirar a tarefa"
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Serviço de tarefas indisponível",
        ) from exc
    return WebAuditCheckResponse(task_id=scan.task_id, status=scan.status)
