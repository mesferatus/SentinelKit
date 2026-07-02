from __future__ import annotations

import json
import logging
from collections.abc import Callable
from typing import Any, TypeVar

from celery import Task
from sqlalchemy import update
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import SessionLocal
from app.models import ScanResult, ScanStatus

logger = logging.getLogger(__name__)

PUBLIC_TASK_ERROR = "Não foi possível concluir a tarefa"
MAX_RESULT_BYTES = 1024 * 1024
ResultT = TypeVar("ResultT", bound=dict[str, Any] | list[Any])


def _update_scan(
    db: Session,
    scan_id: int,
    status: ScanStatus,
    *,
    expected_status: ScanStatus | None = None,
    result: dict[str, Any] | list[Any] | None = None,
    error: str | None = None,
) -> bool:
    statement = (
        update(ScanResult)
        .where(ScanResult.id == scan_id)
        .values(status=status, result=result, error=error)
    )
    if expected_status is not None:
        statement = statement.where(ScanResult.status == expected_status)
    outcome = db.execute(statement)
    db.commit()
    return outcome.rowcount == 1


def _persist_state(
    session_factory: sessionmaker[Session],
    scan_id: int,
    status: ScanStatus,
    **values: Any,
) -> bool:
    with session_factory() as db:
        try:
            return _update_scan(db, scan_id, status, **values)
        except Exception:
            db.rollback()
            raise


def _current_result(
    session_factory: sessionmaker[Session], scan_id: int
) -> dict[str, Any] | list[Any] | None:
    with session_factory() as db:
        scan = db.get(ScanResult, scan_id)
        if scan is None:
            raise LookupError(f"ScanResult {scan_id} não encontrado")
        return scan.result


def _validate_result(result: object) -> None:
    if not isinstance(result, (dict, list)):
        raise ValueError("Resultado da tarefa deve ser objeto ou lista")
    try:
        encoded = json.dumps(
            result, ensure_ascii=False, allow_nan=False, separators=(",", ":")
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ValueError("Resultado da tarefa não é JSON válido") from exc
    if len(encoded) > MAX_RESULT_BYTES:
        raise ValueError("Resultado da tarefa excede o limite permitido")


def execute_scan(
    scan_id: int,
    operation: Callable[[], ResultT],
    *,
    session_factory: sessionmaker[Session] = SessionLocal,
) -> ResultT | dict[str, Any] | list[Any] | None:
    claimed = _persist_state(
        session_factory,
        scan_id,
        ScanStatus.RUNNING,
        expected_status=ScanStatus.PENDING,
    )
    if not claimed:
        return _current_result(session_factory, scan_id)

    try:
        result = operation()
        _validate_result(result)
        completed = _persist_state(
            session_factory,
            scan_id,
            ScanStatus.COMPLETED,
            expected_status=ScanStatus.RUNNING,
            result=result,
            error=None,
        )
        return result if completed else _current_result(session_factory, scan_id)
    except Exception:
        logger.exception("Falha durante execução da tarefa de scan %s", scan_id)
        _persist_state(
            session_factory,
            scan_id,
            ScanStatus.FAILED,
            expected_status=ScanStatus.RUNNING,
            result=None,
            error=PUBLIC_TASK_ERROR,
        )
        raise


class DatabaseScanTask(Task):
    abstract = True

    def execute_scan(
        self,
        scan_id: int,
        operation: Callable[[], ResultT],
    ) -> ResultT | dict[str, Any] | list[Any] | None:
        return execute_scan(scan_id, operation)
