"""
Test fixtures for PayInTable.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.config import config
from app.database import local_session
from app.functions.seed import create_seed_data
from app.models.restaurant import Restaurant
from app.models.location import Location
from app.models.table import Table
from app.models.account import Account
from app.models.account_item import AccountItem
from app.models.staff_user import StaffUser
from app.tests.functions import get_token


@pytest.fixture
async def seeded_data():
    """Create seed data (restaurant, location, tables, admin user)."""
    await create_seed_data()


@pytest.fixture
async def admin_token(async_client: AsyncClient, seeded_data) -> str:
    """Get authentication token for admin user."""
    return await get_token(
        username=config.ADMIN_EMAIL,
        password=config.ADMIN_PASSWORD,
        async_client=async_client,
    )


@pytest.fixture
async def test_restaurant(seeded_data) -> Restaurant:
    """Get the seeded test restaurant."""
    async with local_session() as session:
        stmt = select(Restaurant).where(Restaurant.slug == config.SEED_RESTAURANT_SLUG)
        result = await session.execute(stmt)
        return result.scalar_one()


@pytest.fixture
async def test_location(test_restaurant: Restaurant) -> Location:
    """Get the seeded test location."""
    async with local_session() as session:
        stmt = select(Location).where(
            Location.restaurant_id == test_restaurant.id,
            Location.slug == config.SEED_LOCATION_SLUG,
        )
        result = await session.execute(stmt)
        return result.scalar_one()


@pytest.fixture
async def test_table(test_location: Location) -> Table:
    """Get the first seeded test table."""
    async with local_session() as session:
        stmt = select(Table).where(
            Table.location_id == test_location.id,
            Table.number == 1,
        )
        result = await session.execute(stmt)
        return result.scalar_one()


@pytest.fixture
async def test_account(test_table: Table) -> Account:
    """Create a test account with items for an existing table."""
    async with local_session() as session:
        account = Account(table_id=test_table.id)
        session.add(account)
        await session.commit()
        await session.refresh(account)

        # Add some items
        items = [
            AccountItem(
                account_id=account.id,
                name="Hamburguesa",
                quantity=2,
                unit_price=8500,
            ),
            AccountItem(
                account_id=account.id,
                name="Cerveza",
                quantity=3,
                unit_price=3500,
            ),
        ]
        for item in items:
            session.add(item)
        await session.commit()

        # Reload account with items
        stmt = select(Account).where(Account.id == account.id)
        result = await session.execute(stmt)
        account = result.scalar_one()

        # Load items manually for recalculation
        items_stmt = select(AccountItem).where(AccountItem.account_id == account.id)
        items_result = await session.execute(items_stmt)
        account.items = list(items_result.scalars().all())

        # Recalculate totals
        account.recalculate_totals()
        await session.commit()

        return account
