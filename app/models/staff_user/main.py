from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.functions.hash import check_hash, get_hash

if TYPE_CHECKING:
    from app.models.restaurant import Restaurant


class StaffUser(Base):
    __tablename__ = "staff_user"

    restaurant_id: Mapped[UUID] = mapped_column(
        ForeignKey("restaurant.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(nullable=False)
    email: Mapped[str] = mapped_column(unique=True, nullable=False)
    _password: Mapped[str] = mapped_column(name="password", nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True)

    # Relationships
    restaurant: Mapped["Restaurant"] = relationship(back_populates="staff_users")

    @property
    def password(self) -> str:
        return self._password

    @password.setter
    def password(self, password: str) -> None:
        self._password = get_hash(password)

    def check_password(self, password: str) -> bool:
        return check_hash(password, self.password)
