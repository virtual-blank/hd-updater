from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
import logging
from datetime import timezone, timedelta
import re

log = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_FILE = BASE_DIR / ".env"



class HDSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, env_prefix="HD_", extra="ignore")
    api_key: str
    base_url: str
    admin_api_key: str
    active_hours_polling_period_seconds: int = 60
    inactive_hours_polling_period_seconds: int = 180
    active_hours_start: str = "7:00"
    active_hours_end: str = "22:00"
    timezone: str = "UTC+3"

    @property
    def endpoint(self) -> str:
        if not self.base_url.startswith("https://"):
            raise ValueError("Неверный helpdesk URL")
        return f"{self.base_url.rstrip('/')}/sdpapi/request"

    @property
    def tzinfo(self) -> timezone:
        match = re.match(r"^UTC([+-]\d+)$", self.timezone.strip(), re.IGNORECASE)
        offset_hours = int(match.group(1)) if match else 3
        return timezone(timedelta(hours=offset_hours))


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


class PostgresSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, env_prefix="POSTGRES_", extra="ignore")
    user: str
    password: str
    host: str
    port: int
    name: str

    @property
    def url(self) -> str:
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"


class LoggingSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, env_prefix="LOG_", extra="ignore")
    level: str = "DEBUG"
    format: str = "%(asctime)s [%(levelname)s] %(name)s - %(message)s"


@lru_cache
def get_logging_settings() -> LoggingSettings:
    return LoggingSettings()


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
def get_postgres_settings() -> PostgresSettings:
    return PostgresSettings()
