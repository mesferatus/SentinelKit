from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError, StatementError
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models import (
    AuditLog,
    AuthorizedTarget,
    RefreshToken,
    ScanResult,
    ScanStatus,
    ScanType,
    SiemAnalysis,
    User,
)


@pytest.fixture()
def session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        yield db


def utc_future(days: int = 1) -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=days)


def create_user(session: Session, email: str = "ana@example.com") -> User:
    user = User(name="Usuário de Teste", email=email, password_hash="hashed-password")
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def create_target(session: Session, user: User) -> AuthorizedTarget:
    target = AuthorizedTarget(
        user_id=user.id,
        target="example.com",
        evidence="Servidor de laboratório sob minha responsabilidade.",
        confirmed=True,
        expires_at=utc_future(),
        active=True,
    )
    session.add(target)
    session.commit()
    session.refresh(target)
    return target


def test_creates_complete_domain_graph(session: Session) -> None:
    user = create_user(session)
    target = create_target(session, user)
    refresh = RefreshToken(
        user_id=user.id,
        token_hash="refresh-hash",
        session_id="session-001",
        expires_at=utc_future(days=7),
    )
    scan = ScanResult(
        user_id=user.id,
        type=ScanType.RECON,
        target_id=target.id,
        task_id="celery-task-001",
        status=ScanStatus.COMPLETED,
        result={"open_ports": [80, 443]},
    )
    audit = AuditLog(
        user_id=user.id,
        endpoint="/recon",
        method="POST",
        source_ip="127.0.0.1",
        status_code=202,
    )
    analysis = SiemAnalysis(
        user_id=user.id,
        source="uploaded-access.log",
        summary={"total": 1, "alerts": 1},
        events=[{"type": "sqli", "severity": "high"}],
    )
    session.add_all([refresh, scan, audit, analysis])
    session.commit()
    session.refresh(user)

    assert user.targets == [target]
    assert user.refresh_tokens == [refresh]
    assert user.scan_results == [scan]
    assert user.audit_logs == [audit]
    assert user.siem_analyses == [analysis]
    assert target.scan_results == [scan]
    assert scan.result == {"open_ports": [80, 443]}
    assert analysis.events[0]["type"] == "sqli"
    assert all(
        value.tzinfo is not None
        for value in (
            user.created_at,
            target.created_at,
            refresh.created_at,
            scan.created_at,
            audit.timestamp,
            analysis.timestamp,
        )
    )


def test_rejects_duplicate_user_email(session: Session) -> None:
    create_user(session)
    session.add(User(name="Ana Silva", email="ana@example.com", password_hash="another-hash"))

    with pytest.raises(IntegrityError):
        session.commit()


def test_rejects_duplicate_target_for_same_user(session: Session) -> None:
    user = create_user(session)
    create_target(session, user)
    session.add(
        AuthorizedTarget(
            user_id=user.id,
            target="example.com",
            evidence="Duplicated target",
            confirmed=True,
            expires_at=utc_future(),
        )
    )

    with pytest.raises(IntegrityError):
        session.commit()


def test_allows_same_target_for_different_users(session: Session) -> None:
    first = create_user(session, "first@example.com")
    second = create_user(session, "second@example.com")
    create_target(session, first)
    session.add(
        AuthorizedTarget(
            user_id=second.id,
            target="example.com",
            evidence="Second owner",
            confirmed=True,
            expires_at=utc_future(),
        )
    )

    session.commit()


def test_rejects_unconfirmed_authorized_target(session: Session) -> None:
    user = create_user(session)
    session.add(
        AuthorizedTarget(
            user_id=user.id,
            target="example.com",
            evidence="Missing confirmation",
            confirmed=False,
            expires_at=utc_future(),
        )
    )

    with pytest.raises(IntegrityError):
        session.commit()


def test_rejects_duplicate_refresh_hash_and_session(session: Session) -> None:
    user = create_user(session)
    session.add(
        RefreshToken(
            user_id=user.id,
            token_hash="same-hash",
            session_id="same-session",
            expires_at=utc_future(),
        )
    )
    session.commit()
    session.add(
        RefreshToken(
            user_id=user.id,
            token_hash="same-hash",
            session_id="other-session",
            expires_at=utc_future(),
        )
    )

    with pytest.raises(IntegrityError):
        session.commit()


def test_refresh_token_can_point_to_its_replacement(session: Session) -> None:
    user = create_user(session)
    old = RefreshToken(
        user_id=user.id,
        token_hash="old-hash",
        session_id="session-rotation",
        expires_at=utc_future(),
    )
    new = RefreshToken(
        user_id=user.id,
        token_hash="new-hash",
        session_id="session-rotation-next",
        expires_at=utc_future(),
    )
    session.add_all([old, new])
    session.flush()
    old.replaced_by_id = new.id
    old.revoked_at = datetime.now(timezone.utc)
    session.commit()
    session.refresh(old)

    assert old.replaced_by == new


def test_rejects_invalid_scan_enum_values(session: Session) -> None:
    user = create_user(session)
    target = create_target(session, user)
    session.add(
        ScanResult(
            user_id=user.id,
            type="invalid",
            target_id=target.id,
            task_id="invalid-enum-task",
            status="unknown",
        )
    )

    with pytest.raises((IntegrityError, StatementError, ValueError, LookupError)):
        session.commit()


def test_rejects_duplicate_scan_task_id(session: Session) -> None:
    user = create_user(session)
    target = create_target(session, user)
    session.add_all(
        [
            ScanResult(
                user_id=user.id,
                type=ScanType.RECON,
                target_id=target.id,
                task_id="same-task",
                status=ScanStatus.PENDING,
            ),
            ScanResult(
                user_id=user.id,
                type=ScanType.WEBAUDIT,
                target_id=target.id,
                task_id="same-task",
                status=ScanStatus.PENDING,
            ),
        ]
    )

    with pytest.raises(IntegrityError):
        session.commit()


def test_rejects_scan_for_target_owned_by_another_user(session: Session) -> None:
    owner = create_user(session, "owner@example.com")
    intruder = create_user(session, "intruder@example.com")
    target = create_target(session, owner)
    session.add(
        ScanResult(
            user_id=intruder.id,
            type=ScanType.RECON,
            target_id=target.id,
            task_id="cross-user-target",
            status=ScanStatus.PENDING,
        )
    )

    with pytest.raises(IntegrityError):
        session.commit()


def test_deleting_user_preserves_audit_log_with_null_user_id(
    session: Session,
) -> None:
    user = create_user(session)
    audit = AuditLog(
        user_id=user.id,
        endpoint="/targets",
        method="GET",
        source_ip="127.0.0.1",
        status_code=200,
    )
    session.add(audit)
    session.commit()
    audit_id = audit.id

    session.delete(user)
    session.commit()

    preserved = session.get(AuditLog, audit_id)
    assert preserved is not None
    assert preserved.user_id is None


def test_sqlite_connections_enable_foreign_keys() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")

    with engine.connect() as connection:
        enabled = connection.execute(text("PRAGMA foreign_keys")).scalar_one()

    assert enabled == 1
