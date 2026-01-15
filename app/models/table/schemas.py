from uuid import UUID

from pydantic import BaseModel

from app.models.table.enums import TableStatus


class TableBase(BaseModel):
    number: int
    status: TableStatus = TableStatus.AVAILABLE


class TableCreate(TableBase):
    location_id: UUID


class TableRead(TableBase):
    id: UUID
    location_id: UUID

    model_config = {"from_attributes": True}


class TableWithAccount(TableRead):
    """Table with its active account information."""
    has_active_account: bool = False
    account_total: int | None = None
