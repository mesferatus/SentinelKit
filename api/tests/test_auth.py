from collections.abc import Generator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.database import Base, get_db
from app.core.rate_limit import limiter
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.routers.auth import router


@pytest.fixture
def session_factory():
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    yield factory
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def client(session_factory) -> Generator[TestClient, None, None]:
    limiter._storage.reset()
    app = FastAPI()
    app.state.limiter = limiter
    app.include_router(router)

    def override_db():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as test_client:
        yield test_client
    limiter._storage.reset()


def register(client: TestClient, email: str = "ana@example.com"):
    return client.post("/auth/register", json={"name": "Ana Silva", "email": email, "password": "segura123", "accepted_terms": True})


def login(client: TestClient, email: str = "ana@example.com"):
    return client.post("/auth/login", json={"email": email, "password": "segura123"})


def test_register_sets_httponly_session_cookies_without_returning_tokens(
    client: TestClient, session_factory
) -> None:
    response = register(client)

    assert response.status_code == 201
    assert "access_token" not in response.json()
    assert "refresh_token" not in response.json()
    assert response.json()["message"] == "Cadastro realizado com sucesso"
    assert settings.refresh_cookie_name not in response.json()
    cookies = response.headers.get_list("set-cookie")
    assert any(
        f"{settings.access_cookie_name}=" in cookie
        and "HttpOnly" in cookie
        and "Path=/" in cookie
        and "SameSite=strict" in cookie
        and f"Max-Age={settings.access_token_expire_minutes * 60}" in cookie
        for cookie in cookies
    )
    assert any(
        f"{settings.refresh_cookie_name}=" in cookie
        and "HttpOnly" in cookie
        and "Path=/auth" in cookie
        and "SameSite=strict" in cookie
        and f"Max-Age={settings.refresh_token_expire_days * 86400}" in cookie
        for cookie in cookies
    )

    with session_factory() as db:
        user = db.scalar(select(User).where(User.email == "ana@example.com"))
        token = db.scalar(select(RefreshToken))
        assert user is not None
        assert user.password_hash != "segura123"
        assert token is not None
        assert token.token_hash != response.cookies[settings.refresh_cookie_name]


def test_duplicate_registration_is_409(client: TestClient) -> None:
    assert register(client).status_code == 201

    response = register(client)

    assert response.status_code == 409
    assert response.json()["detail"] == "Não foi possível criar a conta com esses dados"


def test_invalid_password_shape_is_422(client: TestClient) -> None:
    response = client.post(
        "/auth/register", json={"name": "Ana Silva", "email": "ana@example.com", "password": "semnumero", "accepted_terms": True}
    )

    assert response.status_code == 422


def test_login_rejects_bad_credentials_and_issues_session_on_success(
    client: TestClient,
) -> None:
    register(client)

    bad = client.post(
        "/auth/login", json={"email": "ana@example.com", "password": "errada123"}
    )
    good = login(client)

    assert bad.status_code == 401
    assert bad.json()["detail"] == "Credenciais inválidas"
    assert good.status_code == 200
    assert "access_token" not in good.json()
    assert settings.access_cookie_name in good.cookies
    assert settings.refresh_cookie_name in good.cookies


def test_authenticated_user_can_update_profile(client: TestClient, session_factory) -> None:
    register(client)

    response = client.patch(
        "/auth/profile",
        json={
            "name": "Ana Atualizada",
            "email": "ana.atualizada@example.com",
            "password": "novaSenha123",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "id": 1,
        "name": "Ana Atualizada",
        "email": "ana.atualizada@example.com",
    }

    with session_factory() as db:
        user = db.scalar(select(User).where(User.email == "ana.atualizada@example.com"))
        assert user is not None
        assert user.name == "Ana Atualizada"
        assert user.password_hash != "novaSenha123"

    assert client.post(
        "/auth/login",
        json={"email": "ana.atualizada@example.com", "password": "novaSenha123"},
    ).status_code == 200


def test_profile_update_rejects_email_used_by_another_user(client: TestClient) -> None:
    register(client, "first@example.com")
    register(client, "second@example.com")

    response = client.patch(
        "/auth/profile",
        json={"name": "Segunda Pessoa", "email": "first@example.com"},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Esse e-mail já está em uso"


def test_login_uses_dummy_hash_for_unknown_user_and_same_generic_error(
    client: TestClient, monkeypatch
) -> None:
    checked_hashes: list[str] = []

    def record_verification(password: str, password_hash: str) -> bool:
        checked_hashes.append(password_hash)
        return False

    monkeypatch.setattr(
        "app.services.auth_service.verify_password", record_verification
    )

    response = client.post(
        "/auth/login",
        json={"email": "missing@example.com", "password": "errada123"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Credenciais inválidas"
    assert len(checked_hashes) == 1
    assert checked_hashes[0].startswith("$2")


def test_login_rate_limit_is_five_per_minute_per_ip(client: TestClient) -> None:
    for _ in range(5):
        response = client.post(
            "/auth/login",
            json={"email": "missing@example.com", "password": "errada123"},
        )
        assert response.status_code == 401

    limited = client.post(
        "/auth/login",
        json={"email": "missing@example.com", "password": "errada123"},
    )
    assert limited.status_code == 429


def test_refresh_rotates_token_and_reuse_revokes_session(
    client: TestClient, session_factory
) -> None:
    register_response = register(client)
    old_refresh = register_response.cookies[settings.refresh_cookie_name]

    rotated = client.post(
        "/auth/refresh",
        cookies={settings.refresh_cookie_name: old_refresh},
    )
    new_refresh = rotated.cookies[settings.refresh_cookie_name]

    assert rotated.status_code == 200
    assert "access_token" not in rotated.json()
    assert settings.access_cookie_name in rotated.cookies
    assert new_refresh != old_refresh

    reuse = client.post(
        "/auth/refresh",
        cookies={settings.refresh_cookie_name: old_refresh},
    )
    assert reuse.status_code == 401
    assert reuse.json()["detail"] == "Refresh token reutilizado; sessão revogada"

    rejected_new_token = client.post(
        "/auth/refresh",
        cookies={settings.refresh_cookie_name: new_refresh},
    )
    assert rejected_new_token.status_code == 401

    with session_factory() as db:
        tokens = db.scalars(select(RefreshToken)).all()
        assert len(tokens) == 2
        assert all(token.revoked_at is not None for token in tokens)


def test_refresh_without_cookie_is_401(client: TestClient) -> None:
    response = client.post("/auth/refresh")

    assert response.status_code == 401
    assert response.json()["detail"] == "Refresh token ausente"


def test_logout_revokes_entire_session_and_deletes_cookie(
    client: TestClient, session_factory
) -> None:
    registered = register(client)
    refresh_token = registered.cookies[settings.refresh_cookie_name]

    response = client.post(
        "/auth/logout",
        cookies={settings.refresh_cookie_name: refresh_token},
    )

    assert response.status_code == 204
    assert settings.access_cookie_name not in client.cookies
    assert settings.refresh_cookie_name not in client.cookies
    assert "Max-Age=0" in response.headers["set-cookie"]

    with session_factory() as db:
        tokens = db.scalars(select(RefreshToken)).all()
        assert tokens
        assert all(token.revoked_at is not None for token in tokens)

    refresh = client.post(
        "/auth/refresh",
        cookies={settings.refresh_cookie_name: refresh_token},
    )
    assert refresh.status_code == 401
