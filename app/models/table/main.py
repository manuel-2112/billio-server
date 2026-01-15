from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.table.enums import TableStatus

if TYPE_CHECKING:
    from app.models.location import Location
    from app.models.account import Account


class Table(Base):
    __tablename__ = "table"

    location_id: Mapped[UUID] = mapped_column(
        ForeignKey("location.id", ondelete="CASCADE"), nullable=False
    )
    number: Mapped[int] = mapped_column(nullable=False)
    status: Mapped[TableStatus] = mapped_column(default=TableStatus.AVAILABLE)

    # Relationships
    location: Mapped["Location"] = relationship(back_populates="tables")
    accounts: Mapped[list["Account"]] = relationship(
        back_populates="table", lazy="select", cascade="all, delete-orphan"
    )

    @property
    def active_account(self) -> "Account | None":
        """Returns the currently open account for this table, if any."""
        for account in self.accounts:
            if account.status == "open":
                return account
        return None
