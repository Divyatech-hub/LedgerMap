from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ledgermap.db.base import Base


class Correction(Base):
    __tablename__ = "corrections"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(
        ForeignKey("runs.id", ondelete="CASCADE"), index=True
    )
    line_item_id: Mapped[int] = mapped_column(
        ForeignKey("run_line_items.id", ondelete="CASCADE"), index=True
    )
    chat_message: Mapped[str | None] = mapped_column(Text)
    resulting_code: Mapped[str] = mapped_column(String(64))
    corrected_by: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    run: Mapped["Run"] = relationship(back_populates="corrections")
    line_item: Mapped["RunLineItem"] = relationship(back_populates="corrections")