from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.targets import enforce_network_policy, normalize_target
from app.models.authorized_target import AuthorizedTarget
from app.models.user import User
from app.schemas.targets import TargetCreate


def validate_authorized_target(
    db: Session, user: User, target_id: int
) -> AuthorizedTarget:
    target = db.scalar(
        select(AuthorizedTarget).where(
            AuthorizedTarget.id == target_id, AuthorizedTarget.user_id == user.id
        )
    )
    if target is None:
        raise HTTPException(status_code=404, detail="Alvo autorizado não encontrado")
    if not target.active:
        raise HTTPException(status_code=403, detail="Alvo autorizado foi revogado")
    if target.expires_at <= datetime.now(timezone.utc):
        raise HTTPException(status_code=403, detail="Autorização do alvo expirou")
    enforce_network_policy(target.target)
    return target


class TargetService:
    def __init__(self, db: Session):
        self.db = db

    def create(self, user: User, payload: TargetCreate) -> AuthorizedTarget:
        try:
            normalized = normalize_target(payload.target)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        enforce_network_policy(normalized)
        target = AuthorizedTarget(
            user_id=user.id,
            target=normalized,
            evidence=payload.evidence.strip(),
            confirmed=True,
            expires_at=payload.expires_at,
            active=True,
        )
        self.db.add(target)
        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise HTTPException(status_code=409, detail="Alvo já cadastrado") from exc
        self.db.refresh(target)
        return target

    def list(self, user: User) -> list[AuthorizedTarget]:
        return list(
            self.db.scalars(
                select(AuthorizedTarget)
                .where(AuthorizedTarget.user_id == user.id)
                .order_by(AuthorizedTarget.created_at.desc())
            )
        )

    def owned(self, user: User, target_id: int) -> AuthorizedTarget:
        target = self.db.scalar(
            select(AuthorizedTarget).where(
                AuthorizedTarget.id == target_id,
                AuthorizedTarget.user_id == user.id,
            )
        )
        if target is None:
            raise HTTPException(status_code=404, detail="Alvo autorizado não encontrado")
        return target

    def renew(self, user: User, target_id: int, expires_at: datetime) -> AuthorizedTarget:
        target = self.owned(user, target_id)
        enforce_network_policy(target.target)
        target.expires_at = expires_at
        target.active = True
        self.db.commit()
        self.db.refresh(target)
        return target

    def revoke(self, user: User, target_id: int) -> AuthorizedTarget:
        target = self.owned(user, target_id)
        target.active = False
        self.db.commit()
        self.db.refresh(target)
        return target
