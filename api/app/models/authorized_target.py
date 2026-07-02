from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, UTCDateTime, utc_now

if TYPE_CHECKING:
    from app.models.scan_result import ScanResult
    from app.models.user import User


class AuthorizedTarget(Base):
    __tablename__ = "authorized_targets"
    __table_args__ = (
        UniqueConstraint(
            "id", "user_id", name="uq_authorized_target_id_user_id"
        ),
        UniqueConstraint("user_id", "target", name="uq_authorized_target_user_target"),
        CheckConstraint("confirmed = true", name="ck_authorized_target_confirmed"),
        CheckConstraint("length(target) > 0", name="ck_authorized_target_not_empty"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    target: Mapped[str] = mapped_column(String(255), index=True)
    evidence: Mapped[str] = mapped_column(String(1000))
    confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime(), index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), default=utc_now, onupdate=utc_now
    )

    user: Mapped[User] = relationship(back_populates="targets")
    scan_results: Mapped[list[ScanResult]] = relationship(
        back_populates="target",
        cascade="all, delete-orphan",
        overlaps="user,scan_results",
    )
