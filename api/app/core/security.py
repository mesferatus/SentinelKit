from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from passlib.context import CryptContext

from app.core.config import settings

password_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__truncate_error=True,
)

MAX_BCRYPT_PASSWORD_BYTES = 72


def validate_bcrypt_password_length(password: str) -> None:
    if len(password.encode("utf-8")) > MAX_BCRYPT_PASSWORD_BYTES:
        raise ValueError("A senha não pode exceder 72 bytes em UTF-8")


def hash_password(password: str) -> str:
    validate_bcrypt_password_length(password)
    return password_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    validate_bcrypt_password_length(password)
    return password_context.verify(password, password_hash)


def _encode_token(
    *,
    user_id: int,
    token_type: str,
    secret: str,
    lifetime: timedelta,
    session_id: str | None = None,
) -> tuple[str, dict[str, object]]:
    now = datetime.now(timezone.utc).replace(microsecond=0)
    claims: dict[str, object] = {
        "sub": str(user_id),
        "type": token_type,
        "iat": now,
        "exp": now + lifetime,
        "jti": uuid.uuid4().hex,
    }
    if session_id is not None:
        claims["sid"] = session_id
    token = jwt.encode(claims, secret, algorithm=settings.jwt_algorithm)
    return token, claims


def create_access_token(user_id: int) -> str:
    token, _ = _encode_token(
        user_id=user_id,
        token_type="access",
        secret=settings.jwt_secret,
        lifetime=timedelta(minutes=settings.access_token_expire_minutes),
    )
    return token


def create_refresh_token(
    user_id: int, session_id: str | None = None
) -> tuple[str, dict[str, object]]:
    session_id = session_id or uuid.uuid4().hex
    return _encode_token(
        user_id=user_id,
        token_type="refresh",
        secret=settings.jwt_refresh_secret,
        lifetime=timedelta(days=settings.refresh_token_expire_days),
        session_id=session_id,
    )


def _decode_token(token: str, secret: str, expected_type: str) -> dict[str, object]:
    required_claims = ["sub", "type", "iat", "exp", "jti"]
    if expected_type == "refresh":
        required_claims.append("sid")
    claims = jwt.decode(
        token,
        secret,
        algorithms=[settings.jwt_algorithm],
        options={"require": required_claims},
    )
    if claims.get("type") != expected_type:
        raise jwt.InvalidTokenError(f"Expected {expected_type} token")
    return claims


def decode_access_token(token: str) -> dict[str, object]:
    return _decode_token(token, settings.jwt_secret, "access")


def decode_refresh_token(token: str) -> dict[str, object]:
    return _decode_token(token, settings.jwt_refresh_secret, "refresh")


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def timestamp_to_datetime(value: object) -> datetime:
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc)
    return datetime.fromtimestamp(float(value), tz=timezone.utc)
