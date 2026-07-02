from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.core.config import settings
from app.models import AuthorizedTarget, ScanResult, ScanStatus, ScanType, User


def register(client, email="recon@example.com"):
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
            evidence="Laboratório local autorizado",
            confirmed=True,
            active=True,
            expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        )
        db.add(authorized)
        db.commit()
        return authorized.id


def test_recon_creates_pending_task_with_normalized_ports(
    client, session_factory, monkeypatch
):
    from app.tasks import recon

    headers = register(client)
    target_id = create_target(session_factory, "recon@example.com")
    queued = []
    monkeypatch.setattr(settings, "allowed_scan_targets", ["127.0.0.1"])
    monkeypatch.setattr(recon.run_recon_scan, "delay", lambda scan_id, ports: queued.append((scan_id, ports)))

    response = client.post(
        "/recon/scan",
        headers=headers,
        json={"target_id": target_id, "ports": [443, 80, 443]},
    )

    assert response.status_code == 202, response.json()
    body = response.json()
    assert body["status"] == "pending"
    assert body["task_id"]
    with session_factory() as db:
        scan = db.scalar(select(ScanResult).where(ScanResult.task_id == body["task_id"]))
        assert scan.type == ScanType.RECON
        assert scan.status == ScanStatus.PENDING
        assert queued == [(scan.id, [443, 80])]


def test_recon_rejects_other_users_target(client, session_factory, monkeypatch):
    owner = register(client, "owner-recon@example.com")
    intruder = register(client, "intruder-recon@example.com")
    target_id = create_target(session_factory, "owner-recon@example.com")
    monkeypatch.setattr(settings, "allowed_scan_targets", ["127.0.0.1"])

    response = client.post(
        "/recon/scan", headers=intruder, json={"target_id": target_id}
    )

    assert response.status_code == 404


def test_recon_validates_port_range_and_limit(client, session_factory, monkeypatch):
    headers = register(client, "ports@example.com")
    target_id = create_target(session_factory, "ports@example.com")
    monkeypatch.setattr(settings, "allowed_scan_targets", ["127.0.0.1"])
    monkeypatch.setattr(settings, "scan_max_ports", 2)

    assert client.post(
        "/recon/scan", headers=headers, json={"target_id": target_id, "ports": [0]}
    ).status_code == 422
    assert client.post(
        "/recon/scan",
        headers=headers,
        json={"target_id": target_id, "ports": [1, 2, 3]},
    ).status_code == 422


def test_recon_rate_limit_is_ten_per_hour_per_user(
    client, session_factory, monkeypatch
):
    from app.tasks import recon

    headers = register(client, "limited-recon@example.com")
    target_id = create_target(session_factory, "limited-recon@example.com")
    monkeypatch.setattr(settings, "allowed_scan_targets", ["127.0.0.1"])
    monkeypatch.setattr(recon.run_recon_scan, "delay", lambda *args: None)

    for _ in range(10):
        assert client.post(
            "/recon/scan", headers=headers, json={"target_id": target_id}
        ).status_code == 202
    assert client.post(
        "/recon/scan", headers=headers, json={"target_id": target_id}
    ).status_code == 429


def test_worker_revalidates_target_immediately_before_scanning(
    session_factory, monkeypatch
):
    from app.tasks import recon

    with session_factory() as db:
        user = User(name="Worker Recon", email="worker@example.com", password_hash="unused")
        db.add(user)
        db.flush()
        target = AuthorizedTarget(
            user_id=user.id,
            target="127.0.0.1",
            evidence="Laboratório",
            confirmed=True,
            active=False,
            expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        )
        db.add(target)
        db.flush()
        scan = ScanResult(
            user_id=user.id,
            target_id=target.id,
            task_id="worker-revalidate",
            type=ScanType.RECON,
        )
        db.add(scan)
        db.commit()
        scan_id = scan.id

    monkeypatch.setattr(recon, "SessionLocal", session_factory)
    monkeypatch.setattr("app.tasks.base.SessionLocal", session_factory)
    monkeypatch.setattr(settings, "allowed_scan_targets", ["127.0.0.1"])

    try:
        recon.run_recon_scan.run(scan_id, [80])
    except Exception:
        pass

    with session_factory() as db:
        assert db.get(ScanResult, scan_id).status == ScanStatus.FAILED


def test_worker_pins_validated_ip_and_does_not_resolve_host_again(
    session_factory, monkeypatch
):
    from app.tasks import recon

    with session_factory() as db:
        user = User(name="Rebind Test", email="rebind@example.com", password_hash="unused")
        db.add(user)
        db.flush()
        target = AuthorizedTarget(
            user_id=user.id,
            target="safe.example",
            evidence="Servidor autorizado",
            confirmed=True,
            active=True,
            expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        )
        db.add(target)
        db.flush()
        scan = ScanResult(
            user_id=user.id,
            target_id=target.id,
            task_id="rebind-task",
            type=ScanType.RECON,
        )
        db.add(scan)
        db.commit()
        scan_id = scan.id

    calls = []
    monkeypatch.setattr(recon, "SessionLocal", session_factory)
    monkeypatch.setattr("app.tasks.base.SessionLocal", session_factory)
    monkeypatch.setattr(
        recon, "resolve_validated_addresses", lambda target: ["93.184.216.34"]
    )

    async def fake_scan(connect_host, ports, *, display_host=None):
        calls.append((connect_host, ports, display_host))
        return {"host": display_host, "ports": [], "duration_ms": 0}

    monkeypatch.setattr(recon, "scan_ports", fake_scan)

    recon.run_recon_scan.run(scan_id, [80])

    assert calls == [("93.184.216.34", [80], "safe.example")]


def test_broker_failure_marks_scan_failed_and_returns_sanitized_503(
    client, session_factory, monkeypatch
):
    from app.tasks import recon

    headers = register(client, "broker@example.com")
    target_id = create_target(session_factory, "broker@example.com")
    monkeypatch.setattr(settings, "allowed_scan_targets", ["127.0.0.1"])
    monkeypatch.setattr(
        recon.run_recon_scan,
        "delay",
        lambda *args: (_ for _ in ()).throw(
            RuntimeError("redis://secret@internal:6379 unavailable")
        ),
    )

    response = client.post(
        "/recon/scan", headers=headers, json={"target_id": target_id, "ports": [80]}
    )

    assert response.status_code == 503
    assert response.json() == {"detail": "Serviço de tarefas indisponível"}
    assert "secret" not in response.text
    with session_factory() as db:
        scan = db.scalar(
            select(ScanResult).where(ScanResult.user_id == 1)
        )
        assert scan.status == ScanStatus.FAILED
        assert scan.error == "Não foi possível enfileirar a tarefa"


def test_tasks_package_combines_base_and_recon_exports():
    import app.tasks as tasks

    assert set(tasks.__all__) == {
        "DatabaseScanTask",
        "execute_scan",
        "run_recon_scan",
        "run_web_audit",
    }
