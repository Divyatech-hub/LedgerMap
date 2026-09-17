from decimal import Decimal

from sqlalchemy import ForeignKey, JSON, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ledgermap.db.base import Base


class RunLineItem(Base):
    __tablename__ = "run_line_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(
        ForeignKey("runs.id", ondelete="CASCADE"), index=True
    )
    raw_name: Mapped[str] = mapped_column(Text)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    row_number: Mapped[int | None]
    ancestors: Mapped[list[str]] = mapped_column(JSON, default=list)
    matched_code: Mapped[str | None] = mapped_column(String(64))
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    method: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(32), default="review")
    review_reason: Mapped[str | None] = mapped_column(Text)

    run: Mapped["Run"] = relationship(back_populates="line_items")
    corrections: Mapped[list["Correction"]] = relationship(
        back_populates="line_item", cascade="all, delete-orphan"
    )