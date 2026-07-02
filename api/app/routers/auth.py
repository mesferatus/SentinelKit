from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.rate_limit import limiter
from app.core.security import hash_password
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.auth import AuthResponse, LoginRequest, ProfileUpdateRequest, RegisterRequest, UserProfile
from app.services.auth_service import AuthError, AuthService, TokenPair

router = APIRouter(prefix="/auth", tags=["auth"])


def _set_access_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=settings.access_cookie_name,
        value=token,
        max_age=settings.access_token_expire_minutes * 60,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="strict",
        domain=settings.cookie_domain,
        path="/",
    )


def _set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=settings.refresh_cookie_name,
        value=token,
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="strict",
        domain=settings.cookie_domain,
        path=settings.cookie_path,
    )


def _auth_response(
    response: Response, pair: TokenPair, message: str
) -> AuthResponse:
    _set_access_cookie(response, pair.access_token)
    _set_refresh_cookie(response, pair.refresh_token)
    return AuthResponse(message=message, user=pair.user)


def _raise_http(error: AuthError) -> None:
    raise HTTPException(status_code=error.status_code, detail=error.detail) from error


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(
    payload: RegisterRequest, response: Response, db: Session = Depends(get_db)
) -> AuthResponse:
    try:
        return _auth_response(
            response,
            AuthService(db).register(payload.name, payload.email, payload.password),
            "Cadastro realizado com sucesso",
        )
    except AuthError as error:
        _raise_http(error)


@router.post("/login", response_model=AuthResponse)
@limiter.limit("5/minute")
def login(
    request: Request,
    payload: LoginRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> AuthResponse:
    try:
        return _auth_response(
            response,
            AuthService(db).login(payload.email, payload.password),
            "Login realizado com sucesso",
        )
    except AuthError as error:
        _raise_http(error)


@router.post("/refresh", response_model=AuthResponse)
def refresh(
    response: Response,
    refresh_token: str | None = Cookie(
        default=None, alias=settings.refresh_cookie_name
    ),
    db: Session = Depends(get_db),
) -> AuthResponse:
    if refresh_token is None:
        raise HTTPException(status_code=401, detail="Refresh token ausente")
    try:
        return _auth_response(
            response,
            AuthService(db).refresh(refresh_token),
            "Sessão renovada",
        )
    except AuthError as error:
        response.delete_cookie(
            settings.refresh_cookie_name,
            domain=settings.cookie_domain,
            path=settings.cookie_path,
        )
        _raise_http(error)


@router.patch("/profile", response_model=UserProfile)
def update_profile(
    payload: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    existing = db.scalar(
        select(User).where(User.email == payload.email, User.id != current_user.id)
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Esse e-mail já está em uso",
        )

    current_user.name = payload.name
    current_user.email = payload.email
    if payload.password:
        current_user.password_hash = hash_password(payload.password)

    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return current_user


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    response_class=Response,
)
def logout(
    response: Response,
    refresh_token: str | None = Cookie(
        default=None, alias=settings.refresh_cookie_name
    ),
    db: Session = Depends(get_db),
) -> None:
    AuthService(db).logout(refresh_token)
    response.delete_cookie(
        settings.access_cookie_name,
        domain=settings.cookie_domain,
        path="/",
        httponly=True,
        secure=settings.cookie_secure,
        samesite="strict",
    )
    response.delete_cookie(
        settings.refresh_cookie_name,
        domain=settings.cookie_domain,
        path=settings.cookie_path,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="strict",
    )
