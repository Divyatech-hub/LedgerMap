from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ledgermap.db.base import Base


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    taxonomies: Mapped[list["Taxonomy"]] = relationship(
        back_populates="client", cascade="all, delete-orphan"
    )
    account_mappings: Mapped[list["AccountMapping"]] = relationship(
        back_populates="client", cascade="all, delete-orphan"
    )
    runs: Mapped[list["Run"]] = relationship(
        back_populates="client", cascade="all, delete-orphan"
    )