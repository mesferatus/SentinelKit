from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, UTCDateTime, utc_now

if TYPE_CHECKING:
    from app.models.user import User


class SiemAnalysis(Base):
    __tablename__ = "siem_analyses"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    source: Mapped[str] = mapped_column(String(255), index=True)
    summary: Mapped[dict[str, Any]] = mapped_column(JSON)
    events: Mapped[list[dict[str, Any]]] = mapped_column(JSON)
    timestamp: Mapped[datetime] = mapped_column(
        UTCDateTime(), default=utc_now, index=True
    )

    user: Mapped[User] = relationship(back_populates="siem_analyses")
