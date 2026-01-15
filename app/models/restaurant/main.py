from typing import TYPE_CHECKING

from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.location import Location
    from app.models.staff_user import StaffUser


class Restaurant(Base):
    __tablename__ = "restaurant"

    name: Mapped[str] = mapped_column(nullable=False)
    slug: Mapped[str] = mapped_column(unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(nullable=False)

    # Relationships
    locations: Mapped[list["Location"]] = relationship(
        back_populates="restaurant", lazy="select", cascade="all, delete-orphan"
    )
    staff_users: Mapped[list["StaffUser"]] = relationship(
        back_populates="restaurant", lazy="select", cascade="all, delete-orphan"
    )
