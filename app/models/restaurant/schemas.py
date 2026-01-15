from uuid import UUID

from pydantic import BaseModel, EmailStr


class RestaurantBase(BaseModel):
    name: str
    slug: str
    email: EmailStr


class RestaurantCreate(RestaurantBase):
    pass


class RestaurantRead(RestaurantBase):
    id: UUID

    model_config = {"from_attributes": True}
