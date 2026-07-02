from __future__ import annotations

import jwt
from fastapi import Cookie, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import settings
from app.core.security import decode_access_token
from app.models.user import User

def get_current_user(
    request: Request,
    access_token: str | None = Cookie(default=None, alias=settings.access_cookie_name),
    db: Session = Depends(get_db),
) -> User:
    scheme, _, header_token = request.headers.get("authorization", "").partition(" ")
    if scheme.lower() == "bearer" and header_token:
        access_token = header_token
    if access_token is None:
        raise HTTPException(status_code=401, detail="Token de acesso ausente")
    try:
        claims = decode_access_token(access_token)
        user_id = int(str(claims["sub"]))
    except (jwt.PyJWTError, KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=401, detail="Token de acesso inválido") from exc
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Token de acesso inválido")
    return user
