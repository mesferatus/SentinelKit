from __future__ import annotations

import logging

import jwt
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core.database import SessionLocal
from app.core.config import settings
from app.core.security import decode_access_token
from app.models.audit_log import AuditLog

logger = logging.getLogger(__name__)


def _authenticated_user_id(request: Request) -> int | None:
    token = request.cookies.get(settings.access_cookie_name)
    scheme, _, header_token = request.headers.get("authorization", "").partition(" ")
    if scheme.lower() == "bearer" and header_token:
        token = header_token
    if not token:
        return None
    try:
        claims = decode_access_token(token)
        return int(str(claims["sub"]))
    except (jwt.PyJWTError, KeyError, TypeError, ValueError):
        return None


def _source_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",", maxsplit=1)[0].strip()[:45]
    return (request.client.host if request.client else "unknown")[:45]


class AuditLoggerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith("/auth/"):
            return await call_next(request)

        user_id = _authenticated_user_id(request)
        response = await call_next(request)
        if user_id is None:
            return response

        session_factory = getattr(
            request.app.state, "audit_session_factory", SessionLocal
        )
        try:
            with session_factory() as db:
                db.add(
                    AuditLog(
                        user_id=user_id,
                        endpoint=request.url.path[:500],
                        method=request.method[:10],
                        source_ip=_source_ip(request),
                        status_code=response.status_code,
                    )
                )
                db.commit()
        except Exception:
            logger.exception("Falha ao persistir log de auditoria")
        return response
