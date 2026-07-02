from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, UTCDateTime, utc_now

if TYPE_CHECKING:
    from app.models.user import User


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    endpoint: Mapped[str] = mapped_column(String(500), index=True)
    method: Mapped[str] = mapped_column(String(10))
    source_ip: Mapped[str] = mapped_column(String(45), index=True)
    status_code: Mapped[int] = mapped_column(Integer, index=True)
    timestamp: Mapped[datetime] = mapped_column(
        UTCDateTime(), default=utc_now, index=True
    )

    user: Mapped[User | None] = relationship(back_populates="audit_logs")
