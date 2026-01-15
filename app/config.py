from functools import cache

from pydantic import EmailStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseConfig(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    ENV_STATE: str = "dev"
    DROP_ENVS: list[str] = ["test", "dev"]  # Allow dropping in dev and test


class Config(BaseConfig):
    # Database
    DB_URL: str = "sqlite+aiosqlite:///payintable.db"

    # Security
    SECRET_KEY: str = "change-this-in-production"
    ALGORITHM: str = "HS512"
    TOKEN_EXPIRE_SECONDS: int = 3600 * 24  # 24 hours
    TOKEN_PATH: str = "api/v1/auth/token"

    # Admin user
    ADMIN_EMAIL: EmailStr = "admin@payintable.com"
    ADMIN_PASSWORD: str = "admin123"

    # Logging
    LOG_LEVEL: str = "DEBUG"

    # Rate limiting
    RATE_LIMITS: tuple[int, int] = (100, 60)

    # Seed data defaults
    SEED_RESTAURANT_NAME: str = "Demo Restaurant"
    SEED_RESTAURANT_SLUG: str = "demo"
    SEED_LOCATION_NAME: str = "Principal"
    SEED_LOCATION_SLUG: str = "principal"

    # Frontend URL (for CORS)
    FRONTEND_URL: str = "http://localhost:3000"

    # Klap payment gateway (to be configured)
    KLAP_API_KEY: str = ""
    KLAP_API_URL: str = "https://api-pasarela-sandbox.mcdesaqa.cl"
    KLAP_WEBHOOK_SECRET: str = ""

    # AWS SES (to be configured)
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "us-east-1"
    AWS_SES_SENDER: str = ""


class TestConfig(Config):
    DB_URL: str = "sqlite+aiosqlite:///test.db"
    LOG_LEVEL: str = "DEBUG"


class DevConfig(Config):
    model_config = SettingsConfigDict(
        env_file=".env", env_prefix="DEV_", extra="ignore"
    )
    DB_URL: str = "sqlite+aiosqlite:///dev.db"
    TOKEN_EXPIRE_SECONDS: int = 3600 * 24 * 7  # 7 days
    LOG_LEVEL: str = "DEBUG"


class ProdConfig(Config):
    model_config = SettingsConfigDict(
        env_file=".env", env_prefix="PROD_", extra="ignore"
    )


@cache
def get_config(env: str = "dev") -> TestConfig | DevConfig | ProdConfig:
    return dict(test=TestConfig, dev=DevConfig, prod=ProdConfig)[env](ENV_STATE=env)


config = get_config(env=BaseConfig().ENV_STATE)
