# backend/core/config.py
from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_FILE = BASE_DIR / ".env"


class HDSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, env_prefix="HD_", extra="ignore")
    api_key: str
    base_url: str
    admin_api_key: str

    @property
    def endpoint(self) -> str:
        if not self.base_url.startswith("https://"):
            raise ValueError("Неверный helpdesk URL")
        return f"{self.base_url.rstrip('/')}/sdpapi/request"


class TelegramSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, env_prefix="TELEGRAM_", extra="ignore")
    bot_token: str


class RedisSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, env_prefix="REDIS_", extra="ignore")
    port: int = 6379
    host: str = "127.0.0.1"
    ttl: int = 86400

    @property
    def url(self) -> str:
        return f"redis://{self.host}:{self.port}/0"


class DBSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, env_prefix="DB_", extra="ignore")
    url: str  # например: postgresql+asyncpg://user:pass@localhost:5432/hd_bot


@lru_cache
def get_hd_settings() -> HDSettings:
    return HDSettings()


@lru_cache
def get_telegram_settings() -> TelegramSettings:
    return TelegramSettings()


@lru_cache
def get_redis_settings() -> RedisSettings:
    return RedisSettings()


@lru_cache
def get_db_settings() -> DBSettings:
    return DBSettings()
