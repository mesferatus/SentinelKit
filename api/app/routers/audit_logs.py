from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.models.audit_log import AuditLog
from app.models.user import User
from app.schemas.audit_logs import AuditLogPage

router = APIRouter(prefix="/audit-logs", tags=["audit-logs"])

@router.get("", response_model=AuditLogPage)
def list_audit_logs(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    owner = AuditLog.user_id == user.id
    total = db.scalar(select(func.count(AuditLog.id)).where(owner)) or 0
    items = db.scalars(select(AuditLog).where(owner).order_by(AuditLog.timestamp.desc(), AuditLog.id.desc()).offset((page - 1) * page_size).limit(page_size)).all()
    return {"total": total, "items": items, "page": page, "page_size": page_size}
