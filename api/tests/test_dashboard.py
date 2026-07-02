from datetime import datetime, timedelta, timezone

from sqlalchemy import event

from app.models import AuthorizedTarget, ScanResult, ScanStatus, ScanType, User
from app.models.audit_log import AuditLog
from app.models.siem_analysis import SiemAnalysis


def _register(client, email: str) -> dict[str, str]:
    response = client.post(
        "/auth/register", json={"name": "Ana Silva", "email": email, "password": "segura123", "accepted_terms": True}
    )
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.cookies['sentinelkit_access']}"}


def _seed_dashboard(session_factory) -> None:
    now = datetime.now(timezone.utc)
    with session_factory() as db:
        owner = db.query(User).filter_by(email="dashboard@example.com").one()
        other = db.query(User).filter_by(email="dashboard-other@example.com").one()
        owner_target = AuthorizedTarget(
            user_id=owner.id,
            target="example.com",
            evidence="Ambiente autorizado",
            confirmed=True,
            active=True,
            expires_at=now + timedelta(days=1),
        )
        other_target = AuthorizedTarget(
            user_id=other.id,
            target="other.example.com",
            evidence="Outro ambiente",
            confirmed=True,
            active=True,
            expires_at=now + timedelta(days=1),
        )
        db.add_all([owner_target, other_target])
        db.flush()
        db.add_all(
            [
                ScanResult(
                    user_id=owner.id,
                    target_id=owner_target.id,
                    task_id="owner-recon",
                    type=ScanType.RECON,
                    status=ScanStatus.COMPLETED,
                    result={"ports": []},
                    created_at=now - timedelta(minutes=5),
                    updated_at=now - timedelta(minutes=5),
                ),
                ScanResult(
                    user_id=owner.id,
                    target_id=owner_target.id,
                    task_id="owner-web-1",
                    type=ScanType.WEBAUDIT,
                    status=ScanStatus.COMPLETED,
                    result={"score": 80},
                    created_at=now - timedelta(minutes=4),
                    updated_at=now - timedelta(minutes=4),
                ),
                ScanResult(
                    user_id=owner.id,
                    target_id=owner_target.id,
                    task_id="owner-web-2",
                    type=ScanType.WEBAUDIT,
                    status=ScanStatus.COMPLETED,
                    result={"score": 60},
                    created_at=now - timedelta(minutes=3),
                    updated_at=now - timedelta(minutes=3),
                ),
                ScanResult(
                    user_id=other.id,
                    target_id=other_target.id,
                    task_id="other-web",
                    type=ScanType.WEBAUDIT,
                    status=ScanStatus.COMPLETED,
                    result={"score": 0},
                    created_at=now,
                    updated_at=now,
                ),
            ]
        )
        db.add_all(
            [
                AuditLog(
                    user_id=owner.id,
                    endpoint="/targets",
                    method="GET",
                    source_ip="127.0.0.1",
                    status_code=200,
                    timestamp=now - timedelta(minutes=2),
                ),
                AuditLog(
                    user_id=other.id,
                    endpoint="/private",
                    method="GET",
                    source_ip="127.0.0.1",
                    status_code=200,
                    timestamp=now + timedelta(minutes=1),
                ),
                SiemAnalysis(
                    user_id=owner.id,
                    source="access.log",
                    summary={"detections": 2},
                    events=[{"type": "sqli"}, {"type": "brute_force"}],
                    timestamp=now - timedelta(minutes=1),
                ),
                SiemAnalysis(
                    user_id=other.id,
                    source="other.log",
                    summary={"detections": 9},
                    events=[{}] * 9,
                    timestamp=now + timedelta(minutes=2),
                ),
            ]
        )
        db.commit()


def test_dashboard_returns_real_isolated_metrics_and_three_recent_activities(
    client, session_factory
) -> None:
    headers = _register(client, "dashboard@example.com")
    _register(client, "dashboard-other@example.com")
    _seed_dashboard(session_factory)

    response = client.get("/dashboard", headers=headers)

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {"scans", "web_score", "alerts", "recent_activity"}
    assert payload["scans"] == 3
    assert payload["web_score"] == 70.0
    assert payload["alerts"] == 2
    assert len(payload["recent_activity"]) == 3
    assert [item["type"] for item in payload["recent_activity"]] == [
        "siem",
        "audit",
        "scan",
    ]
    assert all(
        set(item) == {"type", "title", "status", "timestamp"}
        for item in payload["recent_activity"]
    )
    assert "other" not in str(payload).lower()


def test_dashboard_requires_authentication_and_uses_null_without_web_score(
    client, session_factory
) -> None:
    assert client.get("/dashboard").status_code == 401
    headers = _register(client, "empty-dashboard@example.com")

    response = client.get("/dashboard", headers=headers)

    assert response.status_code == 200
    assert response.json() == {
        "scans": 0,
        "web_score": None,
        "alerts": 0,
        "recent_activity": [],
    }


def test_dashboard_sums_persisted_detection_counts_without_selecting_events(
    client, session_factory
) -> None:
    headers = _register(client, "summary-dashboard@example.com")
    with session_factory() as db:
        user = db.query(User).filter_by(email="summary-dashboard@example.com").one()
        db.add_all(
            [
                SiemAnalysis(
                    user_id=user.id,
                    source="one.log",
                    summary={"detections": 4},
                    events=[{"large": "payload"}] * 20,
                ),
                SiemAnalysis(
                    user_id=user.id,
                    source="two.log",
                    summary={"detections": 3},
                    events=[{"large": "payload"}] * 20,
                ),
            ]
        )
        db.commit()

    statements: list[str] = []
    engine = session_factory.kw["bind"]

    def capture_sql(_conn, _cursor, statement, _parameters, _context, _executemany):
        statements.append(statement.lower())

    event.listen(engine, "before_cursor_execute", capture_sql)
    try:
        response = client.get("/dashboard", headers=headers)
    finally:
        event.remove(engine, "before_cursor_execute", capture_sql)

    assert response.status_code == 200
    assert response.json()["alerts"] == 7
    assert not any("siem_analyses.events" in statement for statement in statements)


def test_dashboard_activity_order_is_deterministic_when_timestamps_tie(
    client, session_factory
) -> None:
    headers = _register(client, "ties-dashboard@example.com")
    tied_at = datetime.now(timezone.utc)
    with session_factory() as db:
        user = db.query(User).filter_by(email="ties-dashboard@example.com").one()
        target = AuthorizedTarget(
            user_id=user.id,
            target="tie.example.com",
            evidence="Ambiente autorizado",
            confirmed=True,
            active=True,
            expires_at=tied_at + timedelta(days=1),
        )
        db.add(target)
        db.flush()
        db.add(
            ScanResult(
                user_id=user.id,
                target_id=target.id,
                task_id="tie-scan",
                type=ScanType.RECON,
                status=ScanStatus.COMPLETED,
                result={},
                created_at=tied_at,
                updated_at=tied_at,
            )
        )
        db.add_all(
            [
                AuditLog(
                    user_id=user.id,
                    endpoint="/older-id",
                    method="GET",
                    source_ip="127.0.0.1",
                    status_code=200,
                    timestamp=tied_at,
                ),
                AuditLog(
                    user_id=user.id,
                    endpoint="/newer-id",
                    method="POST",
                    source_ip="127.0.0.1",
                    status_code=201,
                    timestamp=tied_at,
                ),
                SiemAnalysis(
                    user_id=user.id,
                    source="tie.log",
                    summary={"detections": 1},
                    events=[{"type": "sqli"}],
                    timestamp=tied_at,
                ),
            ]
        )
        db.commit()

    response = client.get("/dashboard", headers=headers)

    assert response.status_code == 200
    assert [
        (item["type"], item["title"]) for item in response.json()["recent_activity"]
    ] == [
        ("siem", "SIEM: tie.log"),
        ("audit", "POST /newer-id"),
        ("audit", "GET /older-id"),
    ]
