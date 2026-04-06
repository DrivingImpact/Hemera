"""Hemera configuration — loads from .env"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    database_url: str = "postgresql://localhost/hemera"
    anthropic_api_key: str = ""
    companies_house_api_key: str = ""
    clerk_secret_key: str = ""
    clerk_publishable_key: str = ""
    clerk_webhook_secret: str = ""

    class Config:
        env_file = ".env"

    @property
    def clerk_jwks_url(self) -> str:
        return ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
