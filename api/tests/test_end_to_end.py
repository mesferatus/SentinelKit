from datetime import datetime, timedelta, timezone

from app.models import ScanResult, ScanStatus


def test_register_target_and_complete_recon_task(client, session_factory, monkeypatch):
    register = client.post(
        "/auth/register",
        json={"name": "Desktop User", "email": "desktop@example.com", "password": "Desktop!Pass123", "accepted_terms": True},
    )
    assert register.status_code == 201

    login = client.post(
        "/auth/login",
        json={"email": "desktop@example.com", "password": "Desktop!Pass123"},
    )
    assert login.status_code == 200
    headers = {"Authorization": f"Bearer {login.cookies['sentinelkit_access']}"}

    target = client.post(
        "/targets",
        headers=headers,
        json={
            "target": "127.0.0.1",
            "confirmed": True,
            "evidence": "Ambiente local do teste desktop",
            "expires_at": (
                datetime.now(timezone.utc) + timedelta(hours=1)
            ).isoformat(),
        },
    )
    assert target.status_code == 201

    def complete_immediately(scan_id, ports):
        with session_factory() as session:
            scan = session.get(ScanResult, scan_id)
            scan.status = ScanStatus.COMPLETED
            scan.result = {
                "host": "127.0.0.1",
                "ports": [{"port": ports[0], "open": False, "banner": None}],
            }
            session.commit()

    monkeypatch.setattr("app.routers.recon.run_recon_scan.delay", complete_immediately)
    queued = client.post(
        "/recon/scan",
        headers=headers,
        json={"target_id": target.json()["id"], "ports": [65534]},
    )
    assert queued.status_code == 202

    result = client.get(f"/tasks/{queued.json()['task_id']}", headers=headers)
    assert result.status_code == 200
    assert result.json()["status"] == "completed"
    assert result.json()["result"]["host"] == "127.0.0.1"
