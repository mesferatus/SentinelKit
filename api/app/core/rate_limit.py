import jwt
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.security import decode_access_token
from app.core.config import settings


def authenticated_user_key(request) -> str:
    token = request.cookies.get(settings.access_cookie_name)
    scheme, _, header_token = request.headers.get("authorization", "").partition(" ")
    if scheme.lower() == "bearer" and header_token:
        token = header_token
    if token:
        try:
            claims = decode_access_token(token)
            user_id = int(str(claims["sub"]))
            return f"user:{user_id}"
        except (jwt.PyJWTError, KeyError, TypeError, ValueError):
            pass
    return get_remote_address(request)


limiter = Limiter(key_func=get_remote_address)
