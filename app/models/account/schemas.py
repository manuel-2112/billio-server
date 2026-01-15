from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, computed_field

from app.models.account.enums import AccountStatus


class AccountItemRead(BaseModel):
    id: UUID
    name: str
    quantity: int
    unit_price: int
    total_price: int
    image_url: str | None = None

    model_config = {"from_attributes": True}


class AccountBase(BaseModel):
    status: AccountStatus = AccountStatus.OPEN
    subtotal: int = 0
    tax: int = 0
    tip: int = 0
    total: int = 0


class AccountRead(AccountBase):
    id: UUID
    table_id: UUID
    payment_method: str | None = None
    paid_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AccountWithItems(AccountRead):
    """Account with all its items for the customer view."""
    items: list[AccountItemRead] = []

    @computed_field
    def items_count(self) -> int:
        return sum(item.quantity for item in self.items)


class AccountForDashboard(AccountRead):
    """Account info for dashboard history view."""
    table_number: int


class TipUpdate(BaseModel):
    """Request body for updating tip."""
    tip_amount: int | None = None
    tip_percentage: int | None = None  # 0, 10, 15, 20
