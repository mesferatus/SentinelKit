import hashlib

from app.core.config import settings


def test_desktop_runtime_health_requires_nonce(client, monkeypatch):
    monkeypatch.setattr(settings, "desktop_runtime_nonce", "desktop-nonce-secret")

    missing = client.get("/health/runtime")
    wrong = client.get(
        "/health/runtime",
        headers={"X-Sentinel-Runtime": "wrong-nonce"},
    )
    valid = client.get(
        "/health/runtime",
        headers={"X-Sentinel-Runtime": "desktop-nonce-secret"},
    )

    assert missing.status_code == 404
    assert wrong.status_code == 404
    assert valid.status_code == 200
    assert valid.json() == {
        "marker": "sentinelkit-desktop",
        "nonce_hash": hashlib.sha256(b"desktop-nonce-secret").hexdigest(),
    }


def test_api_responses_include_security_headers(client):
    response = client.get("/health")

    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["content-security-policy"] == "default-src 'none'"
    assert "max-age=31536000" in response.headers["strict-transport-security"]
    assert "server" not in response.headers
    assert "x-powered-by" not in response.headers
