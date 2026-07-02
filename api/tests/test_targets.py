from datetime import datetime, timedelta, timezone

import socket

import pytest
from sqlalchemy import select

from app.core.config import settings
from app.core.targets import normalize_target, resolve_validated_addresses
from app.models.authorized_target import AuthorizedTarget


def register(client, email="ana@example.com"):
    return client.post("/auth/register", json={"name": "Ana Silva", "email": email, "password": "segura123", "accepted_terms": True})


def auth_headers(client, email="ana@example.com"):
    response = register(client, email)
    return {"Authorization": f"Bearer {response.cookies[settings.access_cookie_name]}"}


def future(days=2):
    return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()


def public_dns(monkeypatch):
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *args, **kwargs: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0))],
    )


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_normalizes_domains_ipv4_ipv6_and_optional_ports():
    assert normalize_target(" Example.COM:443 ") == "example.com:443"
    assert normalize_target("192.0.2.1:22") == "192.0.2.1:22"
    assert normalize_target("[2001:db8::1]:8443") == "[2001:db8::1]:8443"
    assert normalize_target("2001:db8::1") == "2001:db8::1"


def test_resolve_validated_addresses_returns_the_checked_ip_set(monkeypatch):
    monkeypatch.setattr(settings, "allowed_scan_targets", [])
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *args, **kwargs: [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0))
        ],
    )

    assert resolve_validated_addresses("example.com") == ["93.184.216.34"]


def test_create_list_renew_and_revoke_target(client, monkeypatch):
    public_dns(monkeypatch)
    headers = auth_headers(client)
    created = client.post(
        "/targets",
        headers=headers,
        json={
            "target": " Example.COM:443 ",
            "confirmed": True,
            "evidence": "Servidor sob minha responsabilidade",
            "expires_at": future(),
        },
    )
    assert created.status_code == 201
    assert created.json()["target"] == "example.com:443"
    target_id = created.json()["id"]

    listed = client.get("/targets", headers=headers)
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [target_id]

    renewed = client.patch(
        f"/targets/{target_id}/renew",
        headers=headers,
        json={"confirmed": True, "expires_at": future(5)},
    )
    assert renewed.status_code == 200
    assert renewed.json()["active"] is True

    revoked = client.patch(f"/targets/{target_id}/revoke", headers=headers)
    assert revoked.status_code == 200
    assert revoked.json()["active"] is False


def test_requires_confirmation_and_future_expiry(client, monkeypatch):
    public_dns(monkeypatch)
    headers = auth_headers(client)
    payload = {
        "target": "example.com",
        "confirmed": False,
        "evidence": "Meu servidor",
        "expires_at": future(),
    }
    assert client.post("/targets", headers=headers, json=payload).status_code == 422
    payload["confirmed"] = True
    payload["expires_at"] = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
    assert client.post("/targets", headers=headers, json=payload).status_code == 422


def test_blocks_private_literal_unless_allowlisted(client, monkeypatch):
    monkeypatch.setattr(settings, "allowed_scan_targets", [])
    headers = auth_headers(client)
    payload = {
        "target": "127.0.0.1:8000",
        "confirmed": True,
        "evidence": "Laboratório",
        "expires_at": future(),
    }
    denied = client.post("/targets", headers=headers, json=payload)
    assert denied.status_code == 403
    assert "ALLOWED_SCAN_TARGETS" in denied.json()["detail"]

    monkeypatch.setattr(settings, "allowed_scan_targets", ["127.0.0.1"])
    allowed = client.post("/targets", headers=headers, json=payload)
    assert allowed.status_code == 201


def test_blocks_domain_resolving_to_internal_address(client, monkeypatch):
    monkeypatch.setattr(settings, "allowed_scan_targets", [])
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *args, **kwargs: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.8", 0))],
    )
    headers = auth_headers(client)
    response = client.post(
        "/targets",
        headers=headers,
        json={
            "target": "internal.example",
            "confirmed": True,
            "evidence": "Ambiente interno",
            "expires_at": future(),
        },
    )
    assert response.status_code == 403
    assert "endereço interno" in response.json()["detail"]


def test_target_isolation_and_active_validation(client, monkeypatch):
    public_dns(monkeypatch)
    owner = auth_headers(client, "owner@example.com")
    intruder = auth_headers(client, "intruder@example.com")
    created = client.post(
        "/targets",
        headers=owner,
        json={
            "target": "example.com",
            "confirmed": True,
            "evidence": "Meu servidor",
            "expires_at": future(),
        },
    )
    target_id = created.json()["id"]
    assert client.patch(f"/targets/{target_id}/revoke", headers=intruder).status_code == 404
    assert client.get("/targets", headers=intruder).json() == []

    assert client.patch(f"/targets/{target_id}/revoke", headers=owner).status_code == 200
    invalid = client.get(f"/targets/{target_id}/validate", headers=owner)
    assert invalid.status_code == 403
    assert "revogado" in invalid.json()["detail"]


def test_authenticated_rate_limit_separates_users_on_same_ip(client, monkeypatch):
    public_dns(monkeypatch)
    first = auth_headers(client, "first@example.com")
    second = auth_headers(client, "second@example.com")

    for index in range(30):
        response = client.post(
            "/targets",
            headers=first,
            json={
                "target": f"first-{index}.example.com",
                "confirmed": True,
                "evidence": "Servidor autorizado",
                "expires_at": future(),
            },
        )
        assert response.status_code == 201

    assert client.post(
        "/targets",
        headers=first,
        json={
            "target": "first-over-limit.example.com",
            "confirmed": True,
            "evidence": "Servidor autorizado",
            "expires_at": future(),
        },
    ).status_code == 429
    assert client.post(
        "/targets",
        headers=second,
        json={
            "target": "second.example.com",
            "confirmed": True,
            "evidence": "Servidor autorizado",
            "expires_at": future(),
        },
    ).status_code == 201


def test_invalid_bearer_rate_limit_key_falls_back_without_authenticating(client):
    response = client.post(
        "/targets",
        headers={"Authorization": "Bearer definitely.invalid.token"},
        json={
            "target": "example.com",
            "confirmed": True,
            "evidence": "Servidor autorizado",
            "expires_at": future(),
        },
    )
    assert response.status_code == 401


def test_validate_rejects_target_expired_after_creation(
    client, session_factory, monkeypatch
):
    public_dns(monkeypatch)
    headers = auth_headers(client)
    created = client.post(
        "/targets",
        headers=headers,
        json={
            "target": "expired.example.com",
            "confirmed": True,
            "evidence": "Servidor autorizado",
            "expires_at": future(),
        },
    )
    target_id = created.json()["id"]
    with session_factory() as db:
        target = db.scalar(select(AuthorizedTarget).where(AuthorizedTarget.id == target_id))
        target.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        db.commit()

    response = client.get(f"/targets/{target_id}/validate", headers=headers)
    assert response.status_code == 403
    assert "expirou" in response.json()["detail"]


@pytest.mark.parametrize(
    ("address", "category"),
    [
        ("10.0.0.8", "private"),
        ("127.0.0.1", "loopback"),
        ("169.254.1.2", "link-local"),
        ("192.0.2.1", "reserved"),
    ],
)
def test_dns_categories_require_allowlist(client, monkeypatch, address, category):
    monkeypatch.setattr(settings, "allowed_scan_targets", [])
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *args, **kwargs: [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", (address, 0))
        ],
    )
    headers = auth_headers(client, f"{category}@example.com")
    denied = client.post(
        "/targets",
        headers=headers,
        json={
            "target": f"{category}.example.com",
            "confirmed": True,
            "evidence": "Servidor autorizado",
            "expires_at": future(),
        },
    )
    assert denied.status_code == 403
    assert "ALLOWED_SCAN_TARGETS" in denied.json()["detail"]
