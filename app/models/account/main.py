from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.account.enums import AccountStatus

if TYPE_CHECKING:
    from app.models.table import Table
    from app.models.account_item import AccountItem
    from app.models.webhook_log import WebhookLog


class Account(Base):
    __tablename__ = "account"

    table_id: Mapped[UUID] = mapped_column(
        ForeignKey("table.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[AccountStatus] = mapped_column(default=AccountStatus.OPEN)

    # Money fields (all in CLP, no decimals)
    subtotal: Mapped[int] = mapped_column(default=0)
    tax: Mapped[int] = mapped_column(default=0)  # 19% IVA
    tip: Mapped[int] = mapped_column(default=0)
    total: Mapped[int] = mapped_column(default=0)

    # Payment info
    payment_method: Mapped[str | None] = mapped_column(nullable=True)
    klap_order_id: Mapped[str | None] = mapped_column(nullable=True, index=True)
    paid_at: Mapped[datetime | None] = mapped_column(nullable=True)
    transaction_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Relationships
    table: Mapped["Table"] = relationship(back_populates="accounts")
    items: Mapped[list["AccountItem"]] = relationship(
        back_populates="account", lazy="select", cascade="all, delete-orphan"
    )
    webhook_logs: Mapped[list["WebhookLog"]] = relationship(
        back_populates="account", lazy="select", cascade="all, delete-orphan"
    )

    def recalculate_totals(self) -> None:
        """Recalculate subtotal, tax, and total based on items."""
        self.subtotal = sum(item.total_price for item in self.items)
        self.tax = int(self.subtotal * 0.19)  # 19% IVA
        self.total = self.subtotal + self.tax + self.tip

    def set_tip(self, tip_amount: int) -> None:
        """Set tip amount and recalculate total."""
        self.tip = tip_amount
        self.total = self.subtotal + self.tax + self.tip

    def set_tip_percentage(self, percentage: int) -> None:
        """Set tip as percentage of subtotal."""
        self.tip = int(self.subtotal * percentage / 100)
        self.total = self.subtotal + self.tax + self.tip
