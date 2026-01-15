"""
Seed data creation for development and testing.

Creates a sample restaurant with one location and 5 tables.
"""

import logging

from app.config import config
from app.database import local_session
from app.models.restaurant import Restaurant
from app.models.location import Location
from app.models.table import Table
from app.models.staff_user import StaffUser
from app.models.auth.role import Role

logger = logging.getLogger(__name__)


async def create_seed_data():
    """Create initial seed data for the application."""
    async with local_session() as async_session:
        # Check if data already exists
        existing = await Restaurant.find(
            async_session, slug=config.SEED_RESTAURANT_SLUG, raise_=False
        )
        if existing:
            logger.info("Seed data already exists, skipping creation")
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
        for table_number in range(1, 6):
            table = Table(
                location_id=location.id,
                number=table_number,
            )
            await table.save(async_session)
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

        logger.info("Seed data creation completed!")
