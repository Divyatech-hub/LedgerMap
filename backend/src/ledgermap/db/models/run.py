from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ledgermap.db.base import Base


class Run(Base):
    __tablename__ = "runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(
        ForeignKey("clients.id", ondelete="CASCADE"), index=True
    )
    period: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(32), default="created")
    source_type: Mapped[str | None] = mapped_column(String(32))
    original_filename: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    client: Mapped["Client"] = relationship(back_populates="runs")
    line_items: Mapped[list["RunLineItem"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )
    corrections: Mapped[list["Correction"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )