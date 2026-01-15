import logging
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import config
from app.database import engine, local_session

logger = logging.getLogger(__name__)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with local_session() as session:
        yield session


async def create_all():
    """Create all database tables."""
    from app.models.restaurant import Restaurant  # noqa: F401
    from app.models.location import Location  # noqa: F401
    from app.models.table import Table  # noqa: F401
    from app.models.account import Account  # noqa: F401
    from app.models.account_item import AccountItem  # noqa: F401
    from app.models.webhook_log import WebhookLog  # noqa: F401
    from app.models.staff_user import StaffUser  # noqa: F401

    async with engine.begin() as conn:
        logger.info("Creating all tables if they don't exist")
        await conn.run_sync(Restaurant.metadata.create_all)


async def drop_all():
    """Drop all database tables (only in allowed environments)."""
    from app.models.restaurant import Restaurant  # noqa: F401

    if config.ENV_STATE in config.DROP_ENVS:
        async with engine.begin() as conn:
            logger.warning("Dropping all tables")
            await conn.run_sync(Restaurant.metadata.drop_all)
    else:
        logger.warning("Dropping tables not allowed in this environment")
