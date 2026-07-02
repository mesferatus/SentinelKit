from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from app.core.database import SessionLocal
from app.core.targets import resolve_validated_addresses, target_hostname
from app.models import AuthorizedTarget, ScanResult
from app.services.port_scanner import scan_ports
from app.tasks.base import execute_scan
from app.worker import celery_app


@celery_app.task(name="app.tasks.recon.run_recon_scan")
def run_recon_scan(scan_id: int, ports: list[int]):
    def operation():
        with SessionLocal() as db:
            scan = db.get(ScanResult, scan_id)
            if scan is None:
                raise LookupError("Scan não encontrado")
            target = db.get(AuthorizedTarget, scan.target_id)
            if target is None or target.user_id != scan.user_id:
                raise PermissionError("Alvo autorizado não encontrado")
            if not target.active:
                raise PermissionError("Alvo autorizado foi revogado")
            if target.expires_at <= datetime.now(timezone.utc):
                raise PermissionError("Autorização do alvo expirou")
            host = target_hostname(target.target)
            approved_ip = resolve_validated_addresses(target.target)[0]
        return asyncio.run(scan_ports(approved_ip, ports, display_host=host))

    return execute_scan(scan_id, operation, session_factory=SessionLocal)
