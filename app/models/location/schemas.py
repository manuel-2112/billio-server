from uuid import UUID

from pydantic import BaseModel


class LocationBase(BaseModel):
    name: str
    slug: str


class LocationCreate(LocationBase):
    restaurant_id: UUID


class LocationRead(LocationBase):
    id: UUID
    restaurant_id: UUID

    model_config = {"from_attributes": True}
