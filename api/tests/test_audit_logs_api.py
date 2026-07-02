from app.models.audit_log import AuditLog


def _auth(client, email: str) -> dict[str, str]:
    response = client.post("/auth/register", json={"name": "Ana Silva", "email": email, "password": "segura123", "accepted_terms": True})
    return {"Authorization": f"Bearer {response.cookies['sentinelkit_access']}"}


def test_audit_logs_are_paginated_ordered_and_isolated(client, session_factory) -> None:
    headers = _auth(client, "audit-page@example.com")
    other = _auth(client, "audit-other@example.com")
    client.app.state.audit_session_factory = session_factory
    for index in range(3):
        client.get(f"/own-{index}", headers=headers)
    client.get("/other", headers=other)

    response = client.get("/audit-logs?page=1&page_size=2", headers=headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 3
    assert payload["page"] == 1
    assert payload["page_size"] == 2
    assert [item["endpoint"] for item in payload["items"]] == ["/own-2", "/own-1"]
    assert all(item["endpoint"] != "/other" for item in payload["items"])


def test_audit_logs_require_auth_and_validate_pagination(client) -> None:
    assert client.get("/audit-logs").status_code == 401
    headers = _auth(client, "audit-validation@example.com")
    assert client.get("/audit-logs?page=0", headers=headers).status_code == 422
    assert client.get("/audit-logs?page_size=101", headers=headers).status_code == 422
