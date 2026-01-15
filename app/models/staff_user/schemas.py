from uuid import UUID

from pydantic import BaseModel, EmailStr


class StaffUserBase(BaseModel):
    name: str
    email: EmailStr


class StaffUserCreate(StaffUserBase):
    password: str
    restaurant_id: UUID


class StaffUserRead(StaffUserBase):
    id: UUID
    restaurant_id: UUID
    is_active: bool

    model_config = {"from_attributes": True}


class StaffUserLogin(BaseModel):
    email: EmailStr
    password: str
