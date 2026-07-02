from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, UTCDateTime, utc_now

if TYPE_CHECKING:
    from app.models.audit_log import AuditLog
    from app.models.authorized_target import AuthorizedTarget
    from app.models.refresh_token import RefreshToken
    from app.models.scan_result import ScanResult
    from app.models.siem_analysis import SiemAnalysis


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), default=utc_now, onupdate=utc_now
    )

    targets: Mapped[list[AuthorizedTarget]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    refresh_tokens: Mapped[list[RefreshToken]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    scan_results: Mapped[list[ScanResult]] = relationship(
        back_populates="user", cascade="all, delete-orphan", overlaps="target"
    )
    audit_logs: Mapped[list[AuditLog]] = relationship(
        back_populates="user", passive_deletes=True
    )
    siem_analyses: Mapped[list[SiemAnalysis]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
