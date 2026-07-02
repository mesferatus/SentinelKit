from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.models import AuthorizedTarget, ScanResult, ScanStatus, ScanType, User


def register(client, email: str) -> dict[str, str]:
    response = client.post(
        "/auth/register", json={"name": "Ana Silva", "email": email, "password": "segura123", "accepted_terms": True}
    )
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.cookies['sentinelkit_access']}"}


def create_scan(session_factory, email: str, task_id: str) -> int:
    with session_factory() as db:
        user = db.scalar(select(User).where(User.email == email))
        target = AuthorizedTarget(
            user_id=user.id,
            target=f"{task_id}.example.com",
            evidence="Servidor de teste autorizado",
            confirmed=True,
            expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        )
        db.add(target)
        db.flush()
        scan = ScanResult(
            user_id=user.id,
            target_id=target.id,
            task_id=task_id,
            type=ScanType.RECON,
            status=ScanStatus.PENDING,
        )
        db.add(scan)
        db.commit()
        return scan.id


def test_celery_uses_configured_broker_backend_and_eager_mode(monkeypatch):
    monkeypatch.setenv("CELERY_TASK_ALWAYS_EAGER", "true")
    from app.worker import create_celery_app

    celery_app = create_celery_app()

    assert celery_app.conf.broker_url
    assert celery_app.conf.result_backend
    assert celery_app.conf.task_always_eager is True
    assert celery_app.conf.task_eager_propagates is True


def test_scan_task_completes_and_persists_result(session_factory):
    from app.tasks.base import execute_scan

    scan_id = create_scan_for_user(session_factory, "success-task")
    seen_statuses = []

    def operation():
        with session_factory() as db:
            seen_statuses.append(db.get(ScanResult, scan_id).status)
        return {"ports": [80, 443]}

    result = execute_scan(scan_id, operation, session_factory=session_factory)

    assert result == {"ports": [80, 443]}
    assert seen_statuses == [ScanStatus.RUNNING]
    with session_factory() as db:
        scan = db.get(ScanResult, scan_id)
        assert scan.status == ScanStatus.COMPLETED
        assert scan.result == {"ports": [80, 443]}
        assert scan.error is None


def test_scan_task_marks_failure_and_reraises(session_factory):
    from app.tasks.base import PUBLIC_TASK_ERROR, execute_scan

    scan_id = create_scan_for_user(session_factory, "failed-task")

    def operation():
        raise RuntimeError("scanner indisponível")

    with pytest.raises(RuntimeError, match="scanner indisponível"):
        execute_scan(scan_id, operation, session_factory=session_factory)

    with session_factory() as db:
        scan = db.get(ScanResult, scan_id)
        assert scan.status == ScanStatus.FAILED
        assert scan.result is None
        assert scan.error == PUBLIC_TASK_ERROR


def test_duplicate_delivery_does_not_execute_operation(session_factory):
    from app.tasks.base import execute_scan

    scan_id = create_scan_for_user(session_factory, "duplicate-task")
    with session_factory() as db:
        scan = db.get(ScanResult, scan_id)
        scan.status = ScanStatus.COMPLETED
        scan.result = {"winner": "first"}
        db.commit()
    calls = []

    result = execute_scan(
        scan_id, lambda: calls.append("executed"), session_factory=session_factory
    )

    assert calls == []
    assert result == {"winner": "first"}


def test_late_duplicate_failure_does_not_overwrite_completed_result(session_factory):
    from app.tasks.base import execute_scan

    scan_id = create_scan_for_user(session_factory, "late-duplicate-task")

    def operation():
        with session_factory() as db:
            scan = db.get(ScanResult, scan_id)
            scan.status = ScanStatus.COMPLETED
            scan.result = {"winner": "other-worker"}
            db.commit()
        raise RuntimeError("late duplicate secret C:\\private\\token.txt")

    with pytest.raises(RuntimeError):
        execute_scan(scan_id, operation, session_factory=session_factory)

    with session_factory() as db:
        scan = db.get(ScanResult, scan_id)
        assert scan.status == ScanStatus.COMPLETED
        assert scan.result == {"winner": "other-worker"}
        assert scan.error is None


def test_failure_is_logged_but_persisted_and_returned_error_is_sanitized(
    client, session_factory, caplog
):
    from app.tasks.base import PUBLIC_TASK_ERROR, execute_scan

    headers = register(client, "safe-error@example.com")
    scan_id = create_scan(session_factory, "safe-error@example.com", "safe-error")
    secret = "DATABASE_PASSWORD=topsecret C:\\private\\config.env"

    with pytest.raises(RuntimeError):
        execute_scan(
            scan_id,
            lambda: (_ for _ in ()).throw(RuntimeError(secret)),
            session_factory=session_factory,
        )

    with session_factory() as db:
        assert db.get(ScanResult, scan_id).error == PUBLIC_TASK_ERROR
    response = client.get("/tasks/safe-error", headers=headers)
    assert response.json()["error"] == PUBLIC_TASK_ERROR
    assert secret not in response.text
    assert secret in caplog.text


@pytest.mark.parametrize(
    "result",
    [
        {"invalid": object()},
        {"oversized": "x" * (1024 * 1024)},
    ],
)
def test_invalid_or_oversized_result_is_rejected_and_sanitized(
    session_factory, result
):
    from app.tasks.base import PUBLIC_TASK_ERROR, execute_scan

    scan_id = create_scan_for_user(session_factory, f"bad-result-{id(result)}")

    with pytest.raises(ValueError):
        execute_scan(scan_id, lambda: result, session_factory=session_factory)

    with session_factory() as db:
        scan = db.get(ScanResult, scan_id)
        assert scan.status == ScanStatus.FAILED
        assert scan.result is None
        assert scan.error == PUBLIC_TASK_ERROR


@pytest.mark.parametrize(
    ("case_name", "scalar"),
    [("string", "texto"), ("number", 42), ("boolean", True), ("null", None)],
)
def test_scalar_result_is_failed_and_task_endpoint_remains_valid(
    client, session_factory, case_name, scalar
):
    from app.tasks.base import PUBLIC_TASK_ERROR, execute_scan

    email = f"scalar-{case_name}@example.com"
    task_id = f"scalar-{case_name}"
    headers = register(client, email)
    scan_id = create_scan(session_factory, email, task_id)

    with pytest.raises(ValueError, match="objeto ou lista"):
        execute_scan(scan_id, lambda: scalar, session_factory=session_factory)

    with session_factory() as db:
        scan = db.get(ScanResult, scan_id)
        assert scan.status == ScanStatus.FAILED
        assert scan.result is None
        assert scan.error == PUBLIC_TASK_ERROR

    response = client.get(f"/tasks/{task_id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "failed"
    assert response.json()["result"] is None
    assert response.json()["error"] == PUBLIC_TASK_ERROR


def test_scan_task_rolls_back_before_recording_failure(session_factory, monkeypatch):
    from app.tasks import base

    scan_id = create_scan_for_user(session_factory, "rollback-task")
    real_update = base._update_scan
    calls = []

    def fail_completed(db, current_scan_id, status, **values):
        calls.append(status)
        if status == ScanStatus.COMPLETED:
            raise RuntimeError("falha ao persistir resultado")
        return real_update(db, current_scan_id, status, **values)

    monkeypatch.setattr(base, "_update_scan", fail_completed)

    with pytest.raises(RuntimeError, match="falha ao persistir resultado"):
        base.execute_scan(
            scan_id, lambda: {"ok": True}, session_factory=session_factory
        )

    assert calls == [ScanStatus.RUNNING, ScanStatus.COMPLETED, ScanStatus.FAILED]
    with session_factory() as db:
        scan = db.get(ScanResult, scan_id)
        assert scan.status == ScanStatus.FAILED
        assert scan.error == base.PUBLIC_TASK_ERROR


def test_get_task_returns_owner_state_and_result(client, session_factory):
    headers = register(client, "owner@example.com")
    create_scan(session_factory, "owner@example.com", "owner-task")
    with session_factory() as db:
        scan = db.scalar(
            select(ScanResult).where(ScanResult.task_id == "owner-task")
        )
        scan.status = ScanStatus.COMPLETED
        scan.result = {"headers": {"server": "test"}}
        db.commit()

    response = client.get("/tasks/owner-task", headers=headers)

    assert response.status_code == 200
    assert response.json() == {
        "task_id": "owner-task",
        "type": "recon",
        "status": "completed",
        "result": {"headers": {"server": "test"}},
        "error": None,
    }


def test_get_task_hides_missing_and_other_users_tasks(client, session_factory):
    owner_headers = register(client, "owner@example.com")
    intruder_headers = register(client, "intruder@example.com")
    create_scan(session_factory, "owner@example.com", "private-task")

    assert client.get("/tasks/missing", headers=owner_headers).status_code == 404
    assert (
        client.get("/tasks/private-task", headers=intruder_headers).status_code == 404
    )


def test_get_task_requires_authentication(client):
    assert client.get("/tasks/anything").status_code == 401


def create_scan_for_user(session_factory, task_id: str) -> int:
    with session_factory() as db:
        user = User(
            name="Usuário de Tarefa",
            email=f"{task_id}@example.com",
            password_hash="not-used-in-this-test",
        )
        db.add(user)
        db.flush()
        target = AuthorizedTarget(
            user_id=user.id,
            target=f"{task_id}.example.com",
            evidence="Servidor de teste autorizado",
            confirmed=True,
            expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        )
        db.add(target)
        db.flush()
        scan = ScanResult(
            user_id=user.id,
            target_id=target.id,
            task_id=task_id,
            type=ScanType.RECON,
        )
        db.add(scan)
        db.commit()
        return scan.id
