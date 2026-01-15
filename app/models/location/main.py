from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.restaurant import Restaurant
    from app.models.table import Table


class Location(Base):
    __tablename__ = "location"

    restaurant_id: Mapped[UUID] = mapped_column(
        ForeignKey("restaurant.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(nullable=False)
    slug: Mapped[str] = mapped_column(nullable=False, index=True)

    # Relationships
    restaurant: Mapped["Restaurant"] = relationship(back_populates="locations")
    tables: Mapped[list["Table"]] = relationship(
        back_populates="location", lazy="select", cascade="all, delete-orphan"
    )
