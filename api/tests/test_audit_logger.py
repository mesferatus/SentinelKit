import logging

from sqlalchemy import select

from app.models.audit_log import AuditLog


def _register(client):
    response = client.post(
        "/auth/register",
        json={"name": "Ana Silva", "email": "audit@example.com", "password": "segura123", "accepted_terms": True},
    )
    assert response.status_code == 201
    return response.cookies["sentinelkit_access"]


def test_authenticated_request_is_audited_after_final_status(
    client, session_factory
) -> None:
    client.app.state.audit_session_factory = session_factory
    token = _register(client)

    response = client.get(
        "/targets",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Forwarded-For": "203.0.113.9",
        },
    )

    assert response.status_code == 200
    with session_factory() as db:
        log = db.scalar(
            select(AuditLog)
            .where(AuditLog.endpoint == "/targets")
            .order_by(AuditLog.id.desc())
        )
        assert log is not None
        assert log.user_id is not None
        assert log.method == "GET"
        assert log.source_ip == "203.0.113.9"
        assert log.status_code == 200
        assert log.timestamp is not None


def test_anonymous_request_and_request_body_are_not_audited(
    client, session_factory
) -> None:
    client.app.state.audit_session_factory = session_factory

    response = client.post(
        "/auth/login",
        json={"email": "nobody@example.com", "password": "secret123"},
    )

    assert response.status_code == 401
    with session_factory() as db:
        assert db.scalars(select(AuditLog)).all() == []


def test_audit_persistence_failure_does_not_change_response(
    client, caplog
) -> None:
    class BrokenSession:
        def __enter__(self):
            raise RuntimeError("database unavailable")

        def __exit__(self, *args):
            return False

    client.app.state.audit_session_factory = lambda: BrokenSession()
    token = _register(client)

    with caplog.at_level(logging.ERROR):
        response = client.get(
            "/targets", headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    assert "Falha ao persistir log de auditoria" in caplog.text
