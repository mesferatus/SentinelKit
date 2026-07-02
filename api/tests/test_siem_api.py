from datetime import datetime, timezone

from sqlalchemy import select

from app.core.config import settings
from app.models.audit_log import AuditLog
from app.models.siem_analysis import SiemAnalysis
from app.models.user import User


def _auth(client, email="siem@example.com"):
    response = client.post(
        "/auth/register", json={"name": "Ana Silva", "email": email, "password": "segura123", "accepted_terms": True}
    )
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.cookies['sentinelkit_access']}"}


def test_upload_analysis_persists_result_and_dashboard_returns_it(
    client, session_factory
) -> None:
    client.app.state.audit_session_factory = session_factory
    headers = _auth(client)
    log = (
        '198.51.100.7 - - [20/Jun/2026:22:10:00 +0000] '
        '"GET /?q=%27%20OR%201%3D1-- HTTP/1.1" 200 42 "-" "pytest"\n'
    )

    response = client.post(
        "/siem/analyze",
        headers=headers,
        data={"source": "upload"},
        files={"file": ("access.log", log.encode("utf-8"), "text/plain")},
    )

    assert response.status_code == 201
    assert response.json()["source"] == "access.log"
    assert response.json()["summary"]["detections"] == 1
    dashboard = client.get("/siem/dashboard", headers=headers)
    assert dashboard.status_code == 200
    assert dashboard.json()["analyses"][0]["id"] == response.json()["id"]
    with session_factory() as db:
        assert db.scalar(select(SiemAnalysis)) is not None


def test_dashboard_returns_recent_analyses_and_only_current_user_activity(
    client, session_factory
) -> None:
    client.app.state.audit_session_factory = session_factory
    headers = _auth(client)
    other_headers = _auth(client, "dashboard-other@example.com")
    client.get("/targets", headers=headers)
    client.get("/missing-current", headers=headers)
    client.get("/missing-other", headers=other_headers)

    response = client.get("/siem/dashboard", headers=headers)

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {"analyses", "recent_activity"}
    assert len(payload["recent_activity"]) == 2
    assert [item["endpoint"] for item in payload["recent_activity"]] == [
        "/missing-current",
        "/targets",
    ]
    assert all(
        set(item)
        == {
            "id",
            "endpoint",
            "method",
            "source_ip",
            "status_code",
            "timestamp",
        }
        for item in payload["recent_activity"]
    )
    assert all(item["endpoint"] != "/missing-other" for item in payload["recent_activity"])


def test_internal_analysis_uses_only_current_users_audit_logs(
    client, session_factory
) -> None:
    client.app.state.audit_session_factory = session_factory
    headers = _auth(client)
    other_headers = _auth(client, "other@example.com")
    client.get("/missing-one", headers=headers)
    client.get("/missing-two", headers=headers)
    client.get("/other-missing", headers=other_headers)

    response = client.post(
        "/siem/analyze", headers=headers, data={"source": "internal"}
    )

    assert response.status_code == 201
    assert response.json()["source"] == "internal_audit_logs"
    assert response.json()["summary"]["total_events"] == 2


def test_upload_rejects_oversize_binary_and_ignores_filename_as_path(
    client, monkeypatch
) -> None:
    headers = _auth(client)
    monkeypatch.setattr(settings, "max_upload_bytes", 20)

    oversize = client.post(
        "/siem/analyze",
        headers=headers,
        data={"source": "upload"},
        files={"file": ("../../secret.log", b"x" * 21, "text/plain")},
    )
    binary = client.post(
        "/siem/analyze",
        headers=headers,
        data={"source": "upload"},
        files={"file": ("attack.log", b"\x00\x01\x02", "application/octet-stream")},
    )

    assert oversize.status_code == 413
    assert binary.status_code == 400


def test_analyze_requires_valid_source_and_file(client) -> None:
    headers = _auth(client)

    missing = client.post(
        "/siem/analyze", headers=headers, data={"source": "upload"}
    )
    invalid = client.post(
        "/siem/analyze", headers=headers, data={"source": "filesystem"}
    )

    assert missing.status_code == 422
    assert invalid.status_code == 422
