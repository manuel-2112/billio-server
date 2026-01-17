"""
Account service - Business logic for managing accounts and items.
"""

import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.functions.exceptions import bad_request, not_found
from app.models.account import Account, AccountStatus
from app.models.account_item import AccountItem
from app.models.table import Table, TableStatus

logger = logging.getLogger(__name__)


async def get_or_create_account(
    session: AsyncSession,
    table_id: UUID,
) -> Account:
    """
    Get the active account for a table, or create a new one if none exists.
    Also updates the table status to OCCUPIED.
    """
    # Find table with active account
    stmt = (
        select(Table)
        .where(Table.id == table_id)
        .options(joinedload(Table.accounts))
    )
    result = await session.execute(stmt)
    table = result.unique().scalar_one_or_none()

    if not table:
        raise not_found("Mesa no encontrada")

    # Check for existing open account
    for account in table.accounts:
        if account.status == AccountStatus.OPEN:
            return account

    # Create new account
    account = Account(table_id=table_id)
    session.add(account)

    # Update table status
    table.status = TableStatus.OCCUPIED
    await session.commit()
    await session.refresh(account)

    logger.info(f"Created new account {account.id} for table {table_id}")
    return account


async def add_item_to_account(
    session: AsyncSession,
    table_id: UUID,
    name: str,
    quantity: int,
    unit_price: int,
    image_url: str | None = None,
) -> Account:
    """
    Add an item to a table's account. Creates account if none exists.
    Recalculates totals after adding.
    """
    if quantity < 1:
        raise bad_request("La cantidad debe ser al menos 1")
    if unit_price < 0:
        raise bad_request("El precio no puede ser negativo")

    # Get or create account
    account = await get_or_create_account(session, table_id)

    # Create item
    item = AccountItem(
        account_id=account.id,
        name=name,
        quantity=quantity,
        unit_price=unit_price,
        total_price=quantity * unit_price,
        image_url=image_url,
    )
    session.add(item)
    await session.commit()

    # Reload account with all items to recalculate
    stmt = (
        select(Account)
        .where(Account.id == account.id)
        .options(joinedload(Account.items))
    )
    result = await session.execute(stmt)
    account = result.unique().scalar_one()

    # Recalculate totals
    account.recalculate_totals()
    await session.commit()

    logger.info(f"Added item '{name}' x{quantity} to account {account.id}")
    return account


async def remove_item_from_account(
    session: AsyncSession,
    item_id: UUID,
) -> Account:
    """
    Remove an item from an account.
    Recalculates totals after removal.
    """
    # Find item with account
    stmt = (
        select(AccountItem)
        .where(AccountItem.id == item_id)
        .options(joinedload(AccountItem.account).joinedload(Account.items))
    )
    result = await session.execute(stmt)
    item = result.unique().scalar_one_or_none()

    if not item:
        raise not_found("Producto no encontrado")

    account = item.account

    if account.status != AccountStatus.OPEN:
        raise bad_request("No se puede modificar una cuenta cerrada")

    # Delete item
    await session.delete(item)
    await session.commit()

    # Reload account with remaining items
    stmt = (
        select(Account)
        .where(Account.id == account.id)
        .options(joinedload(Account.items))
    )
    result = await session.execute(stmt)
    account = result.unique().scalar_one()

    # Recalculate totals
    account.recalculate_totals()
    await session.commit()

    logger.info(f"Removed item {item_id} from account {account.id}")
    return account


async def cancel_account(
    session: AsyncSession,
    account_id: UUID,
) -> Account:
    """
    Cancel an open account and free up the table.
    """
    stmt = (
        select(Account)
        .where(Account.id == account_id)
        .options(joinedload(Account.table), joinedload(Account.items))
    )
    result = await session.execute(stmt)
    account = result.unique().scalar_one_or_none()

    if not account:
        raise not_found("Cuenta no encontrada")

    if account.status != AccountStatus.OPEN:
        raise bad_request("Solo se pueden cancelar cuentas abiertas")

    # Update account status
    account.status = AccountStatus.CANCELLED

    # Free up table
    account.table.status = TableStatus.AVAILABLE

    await session.commit()

    logger.info(f"Cancelled account {account_id}")
    return account


async def mark_account_paid(
    session: AsyncSession,
    account_id: UUID,
    payment_method: str,
    klap_order_id: str | None = None,
    transaction_data: dict | None = None,
) -> Account:
    """
    Mark an account as paid and free up the table.
    Called after successful payment webhook.
    """
    stmt = (
        select(Account)
        .where(Account.id == account_id)
        .options(joinedload(Account.table), joinedload(Account.items))
    )
    result = await session.execute(stmt)
    account = result.unique().scalar_one_or_none()

    if not account:
        raise not_found("Cuenta no encontrada")

    if account.status != AccountStatus.OPEN:
        raise bad_request("La cuenta ya está cerrada")

    # Update account
    account.status = AccountStatus.PAID
    account.payment_method = payment_method
    account.klap_order_id = klap_order_id
    account.paid_at = datetime.now(UTC)
    account.transaction_data = transaction_data

    # Free up table
    account.table.status = TableStatus.AVAILABLE

    await session.commit()

    logger.info(f"Account {account_id} marked as paid via {payment_method}")
    return account
