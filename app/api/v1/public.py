"""
Public API routes for customer-facing operations.

These routes don't require authentication and are accessed by customers
scanning QR codes at their tables.
"""

import logging

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.database.dependencies import sessDep
from app.models.account import Account, AccountStatus
from app.models.account.schemas import AccountWithItems, PublicAccountResponse, TipUpdate
from app.models.location import Location
from app.models.restaurant import Restaurant
from app.models.table import Table

router = APIRouter(tags=["Public"])

logger = logging.getLogger(__name__)


@router.get(
    "/{restaurant_slug}/{location_slug}/{table_number}",
    response_model=PublicAccountResponse,
    status_code=status.HTTP_200_OK,
    summary="Get active account for a table",
    description="Returns the current open account with restaurant context.",
)
async def get_table_account(
    async_session: sessDep,
    restaurant_slug: str,
    location_slug: str,
    table_number: int,
):
    """
    Get the active account for a table with context.
    """
    # Build query to find the table with its active account
    stmt = (
        select(Table)
        .join(Location, Table.location_id == Location.id)
        .join(Restaurant, Location.restaurant_id == Restaurant.id)
        .where(Restaurant.slug == restaurant_slug)
        .where(Location.slug == location_slug)
        .where(Table.number == table_number)
        .options(
            joinedload(Table.accounts).joinedload(Account.items),
            joinedload(Table.location).joinedload(Location.restaurant),
        )
    )

    result = await async_session.execute(stmt)
    table = result.unique().scalar_one_or_none()

    if not table:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mesa no encontrada",
        )

    # Find the open account
    open_account = None
    for account in table.accounts:
        if account.status == AccountStatus.OPEN:
            open_account = account
            break

    if not open_account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No hay cuenta abierta para esta mesa",
        )

    logger.info(
        f"Retrieved account {open_account.id} for table {table_number} "
        f"at {restaurant_slug}/{location_slug}"
    )

    return PublicAccountResponse(
        account=open_account,
        restaurant_name=table.location.restaurant.name,
        location_name=table.location.name,
        table_number=table.number,
    )


@router.patch(
    "/accounts/{account_id}/tip",
    response_model=AccountWithItems,
    status_code=status.HTTP_200_OK,
    summary="Update tip for an account",
    description="Update the tip amount for an account. Can be a fixed amount or percentage.",
)
async def update_account_tip(
    async_session: sessDep,
    account_id: str,
    tip_update: TipUpdate,
):
    """
    Update the tip for an account.

    Either tip_amount (fixed CLP) or tip_percentage (0, 10, 15, 20) can be provided.
    """
    from uuid import UUID

    try:
        account_uuid = UUID(account_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ID de cuenta inválido",
        )

    # Load account with items
    stmt = (
        select(Account)
        .where(Account.id == account_uuid)
        .where(Account.status == AccountStatus.OPEN)
        .options(joinedload(Account.items))
    )

    result = await async_session.execute(stmt)
    account = result.unique().scalar_one_or_none()

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cuenta no encontrada o ya cerrada",
        )

    # Update tip
    if tip_update.tip_percentage is not None:
        account.set_tip_percentage(tip_update.tip_percentage)
    elif tip_update.tip_amount is not None:
        account.set_tip(tip_update.tip_amount)

    await async_session.commit()

    logger.info(f"Updated tip for account {account_id}: {account.tip} CLP")

    return account
