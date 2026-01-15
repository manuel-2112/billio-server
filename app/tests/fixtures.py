"""
Test fixtures for PayInTable.
"""

import pytest
from httpx import AsyncClient

from app.config import config
from app.database import local_session
from app.models.restaurant import Restaurant
from app.models.location import Location
from app.models.table import Table
from app.models.account import Account
from app.models.account_item import AccountItem
from app.models.staff_user import StaffUser
from app.tests.functions import get_token


@pytest.fixture
async def admin_token(async_client: AsyncClient) -> str:
    """Get authentication token for admin user."""
    return await get_token(
        username=config.ADMIN_EMAIL,
        password=config.ADMIN_PASSWORD,
        async_client=async_client,
    )


@pytest.fixture
async def test_restaurant() -> Restaurant:
    """Create a test restaurant."""
    async with local_session() as session:
        restaurant = Restaurant(
            name="Test Restaurant",
            slug="test-restaurant",
            email="test@example.com",
        )
        await restaurant.save(session)
        return restaurant


@pytest.fixture
async def test_location(test_restaurant: Restaurant) -> Location:
    """Create a test location."""
    async with local_session() as session:
        location = Location(
            restaurant_id=test_restaurant.id,
            name="Test Location",
            slug="test-location",
        )
        await location.save(session)
        return location


@pytest.fixture
async def test_table(test_location: Location) -> Table:
    """Create a test table."""
    async with local_session() as session:
        table = Table(
            location_id=test_location.id,
            number=1,
        )
        await table.save(session)
        return table


@pytest.fixture
async def test_account(test_table: Table) -> Account:
    """Create a test account with items."""
    async with local_session() as session:
        account = Account(table_id=test_table.id)
        await account.save(session)

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
            await item.save(session)

        # Recalculate totals
        account.items = items
        account.recalculate_totals()
        await session.commit()

        return account
