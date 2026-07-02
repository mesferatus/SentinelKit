from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import jwt
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import utc_now
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    hash_password,
    hash_refresh_token,
    timestamp_to_datetime,
    verify_password,
)
from app.models.refresh_token import RefreshToken
from app.models.user import User

ACCOUNT_CONFLICT_MESSAGE = "Não foi possível criar a conta com esses dados"
INVALID_CREDENTIALS_MESSAGE = "Credenciais inválidas"
DUMMY_PASSWORD_HASH = hash_password("dummy-password-123")


@dataclass
class AuthError(Exception):
    detail: str
    status_code: int = 401


@dataclass
class TokenPair:
    access_token: str
    refresh_token: str
    user: User


class AuthService:
    def __init__(self, db: Session):
        self.db = db

    def register(self, name: str, email: str, password: str) -> TokenPair:
        if self.db.scalar(select(User).where(User.email == email)) is not None:
            raise AuthError(ACCOUNT_CONFLICT_MESSAGE, 409)
        user = User(name=name, email=email, password_hash=hash_password(password))
        self.db.add(user)
        try:
            self.db.flush()
            pair = self._create_session(user)
            self.db.commit()
            return pair
        except IntegrityError as exc:
            self.db.rollback()
            raise AuthError(ACCOUNT_CONFLICT_MESSAGE, 409) from exc

    def login(self, email: str, password: str) -> TokenPair:
        user = self.db.scalar(select(User).where(User.email == email))
        password_hash = user.password_hash if user is not None else DUMMY_PASSWORD_HASH
        password_matches = verify_password(password, password_hash)
        if user is None or not password_matches:
            raise AuthError(INVALID_CREDENTIALS_MESSAGE)
        pair = self._create_session(user)
        self.db.commit()
        return pair

    def refresh(self, raw_token: str) -> TokenPair:
        claims = self._decode_refresh(raw_token)
        token_hash = hash_refresh_token(raw_token)
        stored = self.db.scalar(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
        if stored is None:
            raise AuthError("Refresh token inválido")
        if stored.session_id != claims.get("sid"):
            raise AuthError("Refresh token inválido")
        if stored.revoked_at is not None:
            self._revoke_chain(stored)
            self.db.commit()
            raise AuthError("Refresh token reutilizado; sessão revogada")
        if stored.expires_at <= utc_now():
            stored.revoked_at = utc_now()
            self.db.commit()
            raise AuthError("Refresh token expirado")

        now = utc_now()
        claimed = self.db.execute(
            update(RefreshToken)
            .where(RefreshToken.id == stored.id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=now)
        )
        if claimed.rowcount != 1:
            self.db.refresh(stored)
            self._revoke_chain(stored)
            self.db.commit()
            raise AuthError("Refresh token reutilizado; sessão revogada")

        user = self.db.get(User, stored.user_id)
        pair, replacement = self._build_refresh(user)
        self.db.add(replacement)
        self.db.flush()
        stored.replaced_by_id = replacement.id
        self.db.commit()
        return pair

    def logout(self, raw_token: str | None) -> None:
        if raw_token is None:
            return
        try:
            claims = decode_refresh_token(raw_token)
        except jwt.PyJWTError:
            return
        stored = self.db.scalar(
            select(RefreshToken).where(
                RefreshToken.token_hash == hash_refresh_token(raw_token)
            )
        )
        if stored is not None and stored.session_id == claims.get("sid"):
            self._revoke_chain(stored)
            self.db.commit()

    def _create_session(self, user: User) -> TokenPair:
        pair, stored = self._build_refresh(user)
        self.db.add(stored)
        return pair

    def _build_refresh(
        self, user: User, session_id: str | None = None
    ) -> tuple[TokenPair, RefreshToken]:
        raw_refresh, claims = create_refresh_token(user.id, session_id)
        stored = RefreshToken(
            user_id=user.id,
            token_hash=hash_refresh_token(raw_refresh),
            session_id=str(claims["sid"]),
            expires_at=timestamp_to_datetime(claims["exp"]),
        )
        return (
            TokenPair(
                access_token=create_access_token(user.id),
                refresh_token=raw_refresh,
                user=user,
            ),
            stored,
        )

    def _revoke_chain(self, token: RefreshToken) -> None:
        pending = [token.id]
        visited: set[int] = set()
        while pending:
            token_id = pending.pop()
            if token_id in visited:
                continue
            visited.add(token_id)
            current = self.db.get(RefreshToken, token_id)
            if current is None:
                continue
            if current.revoked_at is None:
                current.revoked_at = utc_now()
            if current.replaced_by_id is not None:
                pending.append(current.replaced_by_id)
            parent_ids = self.db.scalars(
                select(RefreshToken.id).where(
                    RefreshToken.replaced_by_id == current.id
                )
            ).all()
            pending.extend(parent_ids)

    @staticmethod
    def _decode_refresh(raw_token: str) -> dict[str, object]:
        try:
            return decode_refresh_token(raw_token)
        except jwt.ExpiredSignatureError as exc:
            raise AuthError("Refresh token expirado") from exc
        except jwt.PyJWTError as exc:
            raise AuthError("Refresh token inválido") from exc
