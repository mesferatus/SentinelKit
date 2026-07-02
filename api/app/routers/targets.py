from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rate_limit import authenticated_user_key, limiter
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.targets import TargetCreate, TargetRenew, TargetResponse
from app.services.target_service import TargetService, validate_authorized_target

router = APIRouter(prefix="/targets", tags=["targets"])


@router.post("", response_model=TargetResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute", key_func=authenticated_user_key)
def create_target(
    request: Request,
    payload: TargetCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return TargetService(db).create(user, payload)


@router.get("", response_model=list[TargetResponse])
def list_targets(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    return TargetService(db).list(user)


@router.patch("/{target_id}/renew", response_model=TargetResponse)
def renew_target(
    target_id: int,
    payload: TargetRenew,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return TargetService(db).renew(user, target_id, payload.expires_at)


@router.patch("/{target_id}/revoke", response_model=TargetResponse)
def revoke_target(
    target_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return TargetService(db).revoke(user, target_id)


@router.get("/{target_id}/validate", response_model=TargetResponse)
def validate_target(
    target_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return validate_authorized_target(db, user, target_id)
