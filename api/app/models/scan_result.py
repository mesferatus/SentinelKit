from __future__ import annotations

import enum
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Enum, ForeignKey, ForeignKeyConstraint, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, UTCDateTime, utc_now

if TYPE_CHECKING:
    from app.models.authorized_target import AuthorizedTarget
    from app.models.user import User


class ScanType(str, enum.Enum):
    RECON = "recon"
    WEBAUDIT = "webaudit"


class ScanStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ScanResult(Base):
    __tablename__ = "scan_results"
    __table_args__ = (
        ForeignKeyConstraint(
            ["target_id", "user_id"],
            ["authorized_targets.id", "authorized_targets.user_id"],
            name="fk_scan_result_target_owner",
            ondelete="CASCADE",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    type: Mapped[ScanType] = mapped_column(
        Enum(
            ScanType,
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            name="scan_type",
            values_callable=lambda values: [item.value for item in values],
        ),
        index=True,
    )
    target_id: Mapped[int] = mapped_column(index=True)
    task_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    status: Mapped[ScanStatus] = mapped_column(
        Enum(
            ScanStatus,
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            name="scan_status",
            values_callable=lambda values: [item.value for item in values],
        ),
        default=ScanStatus.PENDING,
        index=True,
    )
    result: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(
        JSON, nullable=True
    )
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), default=utc_now, onupdate=utc_now
    )

    user: Mapped[User] = relationship(
        back_populates="scan_results", foreign_keys=[user_id], overlaps="target"
    )
    target: Mapped[AuthorizedTarget] = relationship(
        back_populates="scan_results",
        foreign_keys=[target_id, user_id],
        overlaps="user,scan_results",
    )
