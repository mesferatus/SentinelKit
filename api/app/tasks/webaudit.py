from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from app.core.database import SessionLocal
from app.core.targets import resolve_validated_addresses
from app.models import AuthorizedTarget, ScanResult
from app.services.web_auditor import audit_web_endpoint, validate_webaudit_url
from app.tasks.base import execute_scan
from app.worker import celery_app


@celery_app.task(name="app.tasks.webaudit.run_web_audit")
def run_web_audit(scan_id: int, url: str):
    def operation():
        with SessionLocal() as db:
            scan = db.get(ScanResult, scan_id)
            if scan is None:
                raise LookupError("Scan nao encontrado")
            target = db.get(AuthorizedTarget, scan.target_id)
            if target is None or target.user_id != scan.user_id:
                raise PermissionError("Alvo autorizado nao encontrado")
            if not target.active:
                raise PermissionError("Alvo autorizado foi revogado")
            if target.expires_at <= datetime.now(timezone.utc):
                raise PermissionError("Autorizacao do alvo expirou")
            validate_webaudit_url(target.target, url)
            resolve_validated_addresses(target.target)
            authorized_target = target.target

        return asyncio.run(audit_web_endpoint(authorized_target, url))

    return execute_scan(scan_id, operation, session_factory=SessionLocal)
