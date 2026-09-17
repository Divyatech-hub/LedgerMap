from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ledgermap.db.base import Base


class AccountMapping(Base):
    __tablename__ = "account_mappings"
    __table_args__ = (
        UniqueConstraint(
            "client_id",
            "normalized_raw_name",
            "ancestor_context",
            name="uq_client_account_mapping_context",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(
        ForeignKey("clients.id", ondelete="CASCADE"), index=True
    )
    raw_name: Mapped[str] = mapped_column(Text)
    normalized_raw_name: Mapped[str] = mapped_column(Text)
    ancestor_context: Mapped[str] = mapped_column(Text, default="")
    code: Mapped[str | None] = mapped_column(String(64))
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    method: Mapped[str] = mapped_column(String(32))
    approved_by: Mapped[str | None] = mapped_column(String(255))
    last_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    client: Mapped["Client"] = relationship(back_populates="account_mappings")