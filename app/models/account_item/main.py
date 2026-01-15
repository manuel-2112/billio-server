from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.account import Account


class AccountItem(Base):
    __tablename__ = "account_item"

    account_id: Mapped[UUID] = mapped_column(
        ForeignKey("account.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(nullable=False)
    quantity: Mapped[int] = mapped_column(nullable=False, default=1)
    unit_price: Mapped[int] = mapped_column(nullable=False)  # CLP
    total_price: Mapped[int] = mapped_column(nullable=False)  # quantity * unit_price
    image_url: Mapped[str | None] = mapped_column(nullable=True)

    # Relationships
    account: Mapped["Account"] = relationship(back_populates="items")

    def __init__(self, **kwargs):
        # Auto-calculate total_price if not provided
        if "total_price" not in kwargs and "quantity" in kwargs and "unit_price" in kwargs:
            kwargs["total_price"] = kwargs["quantity"] * kwargs["unit_price"]
        super().__init__(**kwargs)
