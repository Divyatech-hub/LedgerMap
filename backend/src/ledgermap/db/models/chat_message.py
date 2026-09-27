from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ledgermap.db.base import Base


class ChatMessage(Base):
    """One entry in a run's chat-correction conversation, kept so the
    conversation survives a page reload alongside the corrections it led to."""

    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(
        ForeignKey("runs.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String(16))
    text: Mapped[str] = mapped_column(Text)
    candidates: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB)
    """Snapshot of the line items offered to pick from, as they were when the
    assistant replied; only set on ambiguous assistant replies."""
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    run: Mapped["Run"] = relationship(back_populates="chat_messages")
