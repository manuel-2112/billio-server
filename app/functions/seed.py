"""
Seed data creation for development and testing.

Creates a sample restaurant with one location and 5 tables.
Also creates a demo account with items for table 1.
"""

import logging

from app.config import config
from app.database import local_session
from app.models.restaurant import Restaurant
from app.models.location import Location
from app.models.table import Table, TableStatus
from app.models.staff_user import StaffUser
from app.models.auth.role import Role
from app.models.account import Account, AccountStatus
from app.models.account_item import AccountItem

logger = logging.getLogger(__name__)


async def create_seed_data():
    """Create initial seed data for the application."""
    async with local_session() as async_session:
        # Check if data already exists
        existing = await Restaurant.find(
            async_session, slug=config.SEED_RESTAURANT_SLUG, raise_=False
        )
        if existing:
            logger.info("Seed data already exists, checking for demo account...")
            # Try to create demo account for table 1 if it doesn't exist
            await create_demo_account(async_session, existing)
            return

        logger.info("Creating seed data...")

        # Create restaurant
        restaurant = Restaurant(
            name=config.SEED_RESTAURANT_NAME,
            slug=config.SEED_RESTAURANT_SLUG,
            email=config.ADMIN_EMAIL,
        )
        await restaurant.save(async_session)
        logger.info(f"Created restaurant: {restaurant.name} ({restaurant.slug})")

        # Create location
        location = Location(
            restaurant_id=restaurant.id,
            name=config.SEED_LOCATION_NAME,
            slug=config.SEED_LOCATION_SLUG,
        )
        await location.save(async_session)
        logger.info(f"Created location: {location.name} ({location.slug})")

        # Create 5 tables
        tables = []
        for table_number in range(1, 6):
            table = Table(
                location_id=location.id,
                number=table_number,
            )
            await table.save(async_session)
            tables.append(table)
            logger.info(f"Created table: Mesa {table_number}")

        # Create admin staff user
        admin = await StaffUser.find(
            async_session, email=config.ADMIN_EMAIL, raise_=False
        )
        if not admin:
            admin = StaffUser(
                restaurant_id=restaurant.id,
                name="Admin",
                email=config.ADMIN_EMAIL,
                password=config.ADMIN_PASSWORD,
                is_active=True,
            )
            await admin.save(async_session)
            logger.info(f"Created admin staff user: {admin.email}")

        # Create demo account for table 1
        await create_demo_account(async_session, restaurant)

        logger.info("Seed data creation completed!")


async def create_demo_account(async_session, restaurant: Restaurant):
    """Create a demo account with items for table 1."""
    from sqlalchemy import select
    from sqlalchemy.orm import joinedload

    # Find location
    location = await Location.find(
        async_session,
        restaurant_id=restaurant.id,
        slug=config.SEED_LOCATION_SLUG,
        raise_=False,
    )
    if not location:
        logger.warning("Location not found, skipping demo account creation")
        return

    # Find table 1
    stmt = (
        select(Table)
        .where(Table.location_id == location.id)
        .where(Table.number == 1)
        .options(joinedload(Table.accounts))
    )
    result = await async_session.execute(stmt)
    table = result.unique().scalar_one_or_none()

    if not table:
        logger.warning("Table 1 not found, skipping demo account creation")
        return

    # Check if there's already an open account
    has_open_account = any(
        account.status == AccountStatus.OPEN for account in table.accounts
    )

    if has_open_account:
        logger.info("Table 1 already has an open account, skipping demo account creation")
        return

    # Create account
    account = Account(
        table_id=table.id,
        status=AccountStatus.OPEN,
    )
    await account.save(async_session)
    logger.info(f"Created demo account: {account.id}")

    # Update table status
    table.status = TableStatus.OCCUPIED
    await table.save(async_session)

    # Add demo items
    demo_items = [
        AccountItem(
            account_id=account.id,
            name="Hamburguesa Clásica",
            quantity=2,
            unit_price=8500,
            total_price=17000,
        ),
        AccountItem(
            account_id=account.id,
            name="Cerveza Artesanal",
            quantity=3,
            unit_price=3500,
            total_price=10500,
        ),
        AccountItem(
            account_id=account.id,
            name="Papas Fritas",
            quantity=1,
            unit_price=2500,
            total_price=2500,
        ),
    ]

    for item in demo_items:
        await item.save(async_session)

    await async_session.commit()  # Commit items first

    # Reload account with items before recalculating
    stmt = (
        select(Account)
        .where(Account.id == account.id)
        .options(joinedload(Account.items))
    )
    result = await async_session.execute(stmt)
    account = result.unique().scalar_one()

    # Now recalculate totals with items loaded
    account.recalculate_totals()
    await account.save(async_session)

    logger.info(
        f"Created demo account for table 1 with {len(demo_items)} items. "
        f"Total: ${account.total:,} CLP"
    )
