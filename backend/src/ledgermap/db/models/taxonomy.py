from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ledgermap.db.base import Base


class Taxonomy(Base):
    __tablename__ = "taxonomies"

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(
        ForeignKey("clients.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    client: Mapped["Client"] = relationship(back_populates="taxonomies")
    entries: Mapped[list["TaxonomyEntry"]] = relationship(
        back_populates="taxonomy", cascade="all, delete-orphan"
    )


class TaxonomyEntry(Base):
    __tablename__ = "taxonomy_entries"
    __table_args__ = (
        UniqueConstraint("taxonomy_id", "code", name="uq_taxonomy_entry_code"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    taxonomy_id: Mapped[int] = mapped_column(
        ForeignKey("taxonomies.id", ondelete="CASCADE"), index=True
    )
    code: Mapped[str] = mapped_column(String(64))
    description: Mapped[str] = mapped_column(Text)

    taxonomy: Mapped["Taxonomy"] = relationship(back_populates="entries")