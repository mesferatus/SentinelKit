from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.core.config import settings
from app.models import AuthorizedTarget, ScanResult, ScanStatus, ScanType, User


def register(client, email="webaudit@example.com"):
    response = client.post(
        "/auth/register", json={"name": "Ana Silva", "email": email, "password": "segura123", "accepted_terms": True}
    )
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.cookies['sentinelkit_access']}"}


def create_target(session_factory, email, target="127.0.0.1"):
    with session_factory() as db:
        user = db.scalar(select(User).where(User.email == email))
        authorized = AuthorizedTarget(
            user_id=user.id,
            target=target,
            evidence="Laboratorio web autorizado",
            confirmed=True,
            active=True,
            expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        )
        db.add(authorized)
        db.commit()
        return authorized.id


def test_webaudit_creates_pending_task_for_authorized_target(
    client, session_factory, monkeypatch
):
    import app.tasks.webaudit as webaudit

    headers = register(client)
    target_id = create_target(session_factory, "webaudit@example.com")
    queued = []
    monkeypatch.setattr(settings, "allowed_scan_targets", ["127.0.0.1"])
    monkeypatch.setattr(
        webaudit.run_web_audit,
        "delay",
        lambda scan_id, url: queued.append((scan_id, url)),
    )

    response = client.post(
        "/webaudit/check",
        headers=headers,
        json={"target_id": target_id, "url": "https://127.0.0.1/dashboard"},
    )

    assert response.status_code == 202, response.json()
    body = response.json()
    assert body["status"] == "pending"
    assert body["task_id"]
    with session_factory() as db:
        scan = db.scalar(select(ScanResult).where(ScanResult.task_id == body["task_id"]))
        assert scan.type == ScanType.WEBAUDIT
        assert scan.status == ScanStatus.PENDING
        assert queued == [(scan.id, "https://127.0.0.1/dashboard")]


def test_webaudit_rejects_url_that_does_not_match_authorized_target(
    client, session_factory, monkeypatch
):
    headers = register(client, "mismatch@example.com")
    target_id = create_target(session_factory, "mismatch@example.com")
    monkeypatch.setattr(settings, "allowed_scan_targets", ["127.0.0.1"])

    response = client.post(
        "/webaudit/check",
        headers=headers,
        json={"target_id": target_id, "url": "https://example.com/dashboard"},
    )

    assert response.status_code == 422
    assert "alvo autorizado" in response.json()["detail"]


def test_webaudit_rate_limit_is_ten_per_hour_per_user(
    client, session_factory, monkeypatch
):
    import app.tasks.webaudit as webaudit

    headers = register(client, "limited-webaudit@example.com")
    target_id = create_target(session_factory, "limited-webaudit@example.com")
    monkeypatch.setattr(settings, "allowed_scan_targets", ["127.0.0.1"])
    monkeypatch.setattr(webaudit.run_web_audit, "delay", lambda *args: None)

    for _ in range(10):
        assert client.post(
            "/webaudit/check",
            headers=headers,
            json={"target_id": target_id, "url": "https://127.0.0.1/"},
        ).status_code == 202
    assert client.post(
        "/webaudit/check",
        headers=headers,
        json={"target_id": target_id, "url": "https://127.0.0.1/"},
    ).status_code == 429


def test_webaudit_broker_failure_marks_scan_failed_and_returns_sanitized_503(
    client, session_factory, monkeypatch
):
    import app.tasks.webaudit as webaudit

    headers = register(client, "broker-webaudit@example.com")
    target_id = create_target(session_factory, "broker-webaudit@example.com")
    monkeypatch.setattr(settings, "allowed_scan_targets", ["127.0.0.1"])
    monkeypatch.setattr(
        webaudit.run_web_audit,
        "delay",
        lambda *args: (_ for _ in ()).throw(
            RuntimeError("redis://secret@internal:6379 unavailable")
        ),
    )

    response = client.post(
        "/webaudit/check",
        headers=headers,
        json={"target_id": target_id, "url": "https://127.0.0.1/"},
    )

    assert response.status_code == 503
    assert response.json() == {"detail": "Serviço de tarefas indisponível"}
    assert "secret" not in response.text
    with session_factory() as db:
        scan = db.scalar(select(ScanResult).where(ScanResult.user_id == 1))
        assert scan.status == ScanStatus.FAILED
        assert scan.error == "Não foi possível enfileirar a tarefa"


def test_webaudit_worker_revalidates_target_immediately_before_auditing(
    session_factory, monkeypatch
):
    import app.tasks.webaudit as webaudit

    with session_factory() as db:
        user = User(name="Worker Web Audit", email="worker-webaudit@example.com", password_hash="unused")
        db.add(user)
        db.flush()
        target = AuthorizedTarget(
            user_id=user.id,
            target="127.0.0.1",
            evidence="Laboratorio",
            confirmed=True,
            active=False,
            expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        )
        db.add(target)
        db.flush()
        scan = ScanResult(
            user_id=user.id,
            target_id=target.id,
            task_id="worker-webaudit",
            type=ScanType.WEBAUDIT,
        )
        db.add(scan)
        db.commit()
        scan_id = scan.id

    monkeypatch.setattr(webaudit, "SessionLocal", session_factory)
    monkeypatch.setattr("app.tasks.base.SessionLocal", session_factory)
    monkeypatch.setattr(settings, "allowed_scan_targets", ["127.0.0.1"])

    try:
        webaudit.run_web_audit.run(scan_id, "https://127.0.0.1/")
    except Exception:
        pass

    with session_factory() as db:
        assert db.get(ScanResult, scan_id).status == ScanStatus.FAILED
