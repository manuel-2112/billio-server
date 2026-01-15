from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class WebhookLogRead(BaseModel):
    id: UUID
    account_id: UUID
    event_type: str
    payload: dict
    response_status: int
    created_at: datetime

    model_config = {"from_attributes": True}
