"""
Dashboard API routes for staff operations.

These routes require authentication and are used by restaurant staff
to manage tables, accounts, and view history.
"""

import logging
from datetime import date, datetime, UTC
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select, and_
from sqlalchemy.orm import joinedload

from app.database.dependencies import sessDep
from app.models.account import Account, AccountStatus
from app.models.account.schemas import AccountWithItems
from app.models.account_item.schemas import AccountItemCreate
from app.models.auth.dependencies import authorizeLoadDep
from app.models.location import Location
from app.models.table import Table, TableStatus
from app.services import account_service

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

logger = logging.getLogger(__name__)


# ============ Schemas ============

class TableStatusResponse(BaseModel):
    """Table with its current status and account info."""
    id: UUID
    number: int
    status: TableStatus
    has_active_account: bool
    account_id: UUID | None = None
    account_total: int | None = None
    items_count: int = 0

    model_config = {"from_attributes": True}


class TablesListResponse(BaseModel):
    """Response for listing all tables."""
    tables: list[TableStatusResponse]
    location_name: str
    restaurant_name: str


class AddItemRequest(BaseModel):
    """Request body for adding an item to a table."""
    name: str
    quantity: int = 1
    unit_price: int
    image_url: str | None = None


class AccountHistoryItem(BaseModel):
    """Account info for history view."""
    id: UUID
    table_number: int
    subtotal: int
    tax: int
    tip: int
    total: int
    payment_method: str | None
    paid_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AccountHistoryResponse(BaseModel):
    """Response for account history."""
    accounts: list[AccountHistoryItem]
    total_revenue: int
    total_tips: int
    count: int


# ============ Routes ============

@router.get(
    "/tables",
    response_model=TablesListResponse,
    status_code=status.HTTP_200_OK,
    summary="List all tables with status",
    description="Get all tables for the staff's restaurant with their current status and active account info.",
)
async def list_tables(
    async_session: sessDep,
    current_user: authorizeLoadDep,
):
    """
    List all tables with their current status.
    Shows if there's an active account and the total amount.
    """
    # Get restaurant and location for current user
    stmt = (
        select(Location)
        .where(Location.restaurant_id == current_user.restaurant_id)
        .options(
            joinedload(Location.restaurant),
            joinedload(Location.tables).joinedload(Table.accounts).joinedload(Account.items),
        )
    )
    result = await async_session.execute(stmt)
    location = result.unique().scalar_one_or_none()

    if not location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontró ubicación para este restaurante",
        )

    # Build response
    tables_response = []
    for table in sorted(location.tables, key=lambda t: t.number):
        # Find active account
        active_account = None
        for account in table.accounts:
            if account.status == AccountStatus.OPEN:
                active_account = account
                break

        tables_response.append(
            TableStatusResponse(
                id=table.id,
                number=table.number,
                status=table.status,
                has_active_account=active_account is not None,
                account_id=active_account.id if active_account else None,
                account_total=active_account.total if active_account else None,
                items_count=sum(item.quantity for item in active_account.items) if active_account else 0,
            )
        )

    logger.info(f"Listed {len(tables_response)} tables for user {current_user.id}")

    return TablesListResponse(
        tables=tables_response,
        location_name=location.name,
        restaurant_name=location.restaurant.name,
    )


@router.get(
    "/tables/{table_id}",
    response_model=AccountWithItems,
    status_code=status.HTTP_200_OK,
    summary="Get table's active account",
    description="Get the active account for a specific table with all items.",
)
async def get_table_account(
    async_session: sessDep,
    current_user: authorizeLoadDep,
    table_id: UUID,
):
    """
    Get the active account for a table.
    Returns 404 if no active account exists.
    """
    stmt = (
        select(Table)
        .where(Table.id == table_id)
        .options(
            joinedload(Table.location),
            joinedload(Table.accounts).joinedload(Account.items),
        )
    )
    result = await async_session.execute(stmt)
    table = result.unique().scalar_one_or_none()

    if not table:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mesa no encontrada",
        )

    # Validate table belongs to user's restaurant
    if table.location.restaurant_id != current_user.restaurant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes acceso a esta mesa",
        )

    # Find active account
    active_account = None
    for account in table.accounts:
        if account.status == AccountStatus.OPEN:
            active_account = account
            break

    if not active_account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No hay cuenta abierta para esta mesa",
        )

    return active_account


@router.post(
    "/tables/{table_id}/items",
    response_model=AccountWithItems,
    status_code=status.HTTP_201_CREATED,
    summary="Add item to table",
    description="Add a product to a table's account. Creates account if none exists.",
)
async def add_item_to_table(
    async_session: sessDep,
    current_user: authorizeLoadDep,
    table_id: UUID,
    item: AddItemRequest,
):
    """
    Add an item to a table's account.
    If no active account exists, one will be created automatically.
    """
    # Validate table belongs to user's restaurant
    stmt = (
        select(Table)
        .where(Table.id == table_id)
        .options(joinedload(Table.location))
    )
    result = await async_session.execute(stmt)
    table = result.unique().scalar_one_or_none()

    if not table:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mesa no encontrada",
        )

    if table.location.restaurant_id != current_user.restaurant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes acceso a esta mesa",
        )

    # Add item using service
    account = await account_service.add_item_to_account(
        session=async_session,
        table_id=table_id,
        name=item.name,
        quantity=item.quantity,
        unit_price=item.unit_price,
        image_url=item.image_url,
    )

    # Reload with items for response
    stmt = (
        select(Account)
        .where(Account.id == account.id)
        .options(joinedload(Account.items))
    )
    result = await async_session.execute(stmt)
    account = result.unique().scalar_one()

    logger.info(f"Staff {current_user.id} added item to table {table_id}")
    return account


@router.delete(
    "/items/{item_id}",
    response_model=AccountWithItems,
    status_code=status.HTTP_200_OK,
    summary="Remove item from account",
    description="Remove a product from an account.",
)
async def remove_item(
    async_session: sessDep,
    current_user: authorizeLoadDep,
    item_id: UUID,
):
    """
    Remove an item from an account.
    Recalculates totals after removal.
    """
    # Remove item using service
    account = await account_service.remove_item_from_account(
        session=async_session,
        item_id=item_id,
    )

    # Reload with items for response
    stmt = (
        select(Account)
        .where(Account.id == account.id)
        .options(joinedload(Account.items))
    )
    result = await async_session.execute(stmt)
    account = result.unique().scalar_one()

    logger.info(f"Staff {current_user.id} removed item {item_id}")
    return account


@router.post(
    "/accounts/{account_id}/cancel",
    response_model=AccountWithItems,
    status_code=status.HTTP_200_OK,
    summary="Cancel an account",
    description="Cancel an open account and free up the table.",
)
async def cancel_account(
    async_session: sessDep,
    current_user: authorizeLoadDep,
    account_id: UUID,
):
    """
    Cancel an open account.
    The table will be marked as available.
    """
    # Cancel using service
    account = await account_service.cancel_account(
        session=async_session,
        account_id=account_id,
    )

    # Reload with items for response
    stmt = (
        select(Account)
        .where(Account.id == account.id)
        .options(joinedload(Account.items))
    )
    result = await async_session.execute(stmt)
    account = result.unique().scalar_one()

    logger.info(f"Staff {current_user.id} cancelled account {account_id}")
    return account


@router.get(
    "/accounts",
    response_model=AccountHistoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get account history",
    description="Get history of paid accounts with optional date filter.",
)
async def get_account_history(
    async_session: sessDep,
    current_user: authorizeLoadDep,
    filter_date: date | None = Query(None, description="Filter by date (YYYY-MM-DD)"),
):
    """
    Get history of paid accounts.
    Defaults to today's accounts if no date is provided.
    """
    # Default to today
    if filter_date is None:
        filter_date = datetime.now(UTC).date()

    # Build query for paid accounts on the specified date
    start_of_day = datetime.combine(filter_date, datetime.min.time())
    end_of_day = datetime.combine(filter_date, datetime.max.time())

    stmt = (
        select(Account)
        .join(Table, Account.table_id == Table.id)
        .join(Location, Table.location_id == Location.id)
        .where(
            and_(
                Location.restaurant_id == current_user.restaurant_id,
                Account.status == AccountStatus.PAID,
                Account.paid_at >= start_of_day,
                Account.paid_at <= end_of_day,
            )
        )
        .options(joinedload(Account.table))
        .order_by(Account.paid_at.desc())
    )

    result = await async_session.execute(stmt)
    accounts = result.unique().scalars().all()

    # Build response
    history_items = []
    total_revenue = 0
    total_tips = 0

    for account in accounts:
        history_items.append(
            AccountHistoryItem(
                id=account.id,
                table_number=account.table.number,
                subtotal=account.subtotal,
                tax=account.tax,
                tip=account.tip,
                total=account.total,
                payment_method=account.payment_method,
                paid_at=account.paid_at,
                created_at=account.created_at,
            )
        )
        total_revenue += account.total
        total_tips += account.tip

    logger.info(
        f"Retrieved {len(history_items)} accounts for date {filter_date} "
        f"for user {current_user.id}"
    )

    return AccountHistoryResponse(
        accounts=history_items,
        total_revenue=total_revenue,
        total_tips=total_tips,
        count=len(history_items),
    )
