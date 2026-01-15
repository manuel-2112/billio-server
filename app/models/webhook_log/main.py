from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.account import Account


class WebhookLog(Base):
    __tablename__ = "webhook_log"

    account_id: Mapped[UUID] = mapped_column(
        ForeignKey("account.id", ondelete="CASCADE"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(nullable=False)  # "confirm" or "reject"
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    response_status: Mapped[int] = mapped_column(nullable=False)

    # Relationships
    account: Mapped["Account"] = relationship(back_populates="webhook_logs")
