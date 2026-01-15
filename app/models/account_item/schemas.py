from uuid import UUID

from pydantic import BaseModel, computed_field


class AccountItemBase(BaseModel):
    name: str
    quantity: int = 1
    unit_price: int
    image_url: str | None = None


class AccountItemCreate(AccountItemBase):
    """Schema for creating a new item in an account."""
    pass

    @computed_field
    def total_price(self) -> int:
        return self.quantity * self.unit_price


class AccountItemRead(AccountItemBase):
    id: UUID
    account_id: UUID
    total_price: int

    model_config = {"from_attributes": True}
