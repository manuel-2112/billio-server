"""
Checkout API routes for payment processing.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.database.dependencies import sessDep
from app.models.account import Account, AccountStatus
from app.models.account.schemas import AccountWithItems
from app.services import account_service
from app.services.klap_service import klap_service

router = APIRouter(prefix="/accounts", tags=["Checkout"])

logger = logging.getLogger(__name__)


class CheckoutRequest(BaseModel):
    """Request body for initiating checkout."""
    tip_amount: int | None = None
    tip_percentage: int | None = None


class CheckoutResponse(BaseModel):
    """Response for checkout initialization."""
    order_id: str
    reference_id: str
    account: AccountWithItems


@router.post(
    "/{account_id}/checkout",
    response_model=CheckoutResponse,
    status_code=status.HTTP_200_OK,
    summary="Initialize payment checkout",
    description="Create a Klap order for an account and return order_id for frontend integration.",
)
async def create_checkout(
    async_session: sessDep,
    account_id: UUID,
    checkout_request: CheckoutRequest,
):
    """
    Initialize checkout process for an account.

    Creates a Klap order and updates the account with tip if provided.
    Returns the Klap order_id which should be used by Klap Elements on the frontend.
    """
    from sqlalchemy.orm import joinedload
    from sqlalchemy import select

    # Load account with items
    stmt = (
        select(Account)
        .where(Account.id == account_id)
        .where(Account.status == AccountStatus.OPEN)
        .options(joinedload(Account.items), joinedload(Account.table))
    )
    result = await async_session.execute(stmt)
    account = result.unique().scalar_one_or_none()

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cuenta no encontrada o ya cerrada",
        )

    # Update tip if provided
    if checkout_request.tip_percentage is not None:
        account.set_tip_percentage(checkout_request.tip_percentage)
        await async_session.commit()
    elif checkout_request.tip_amount is not None:
        account.set_tip(checkout_request.tip_amount)
        await async_session.commit()

    # Ensure totals are up to date
    account.recalculate_totals()
    await async_session.commit()

    # Validate minimum payment
    if account.total < 1000:  # Minimum 1,000 CLP
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El monto mínimo de pago es $1,000 CLP",
        )

    # Generate reference_id
    reference_id = klap_service.generate_reference_id(account.table_id)

    # Create Klap order
    try:
        klap_order = await klap_service.create_order(
            reference_id=reference_id,
            amount=account.total,
            description=f"Pago Mesa {account.table.number} - Cuenta {account.id.hex[:8]}",
        )
    except Exception as e:
        logger.error(f"Failed to create Klap order for account {account_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al crear orden de pago",
        )

    order_id = klap_order.get("order_id")
    if not order_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Klap no retornó order_id",
        )

    # Store Klap order_id in account
    account.klap_order_id = order_id
    await async_session.commit()

    logger.info(
        f"Checkout initialized: account={account_id}, "
        f"order_id={order_id}, reference_id={reference_id}, total={account.total}"
    )

    return CheckoutResponse(
        order_id=order_id,
        reference_id=reference_id,
        account=account,
    )
