from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path
from functools import lru_cache

BASE_URL = Path(__file__).resolve().parent.parent.parent
ENV_FILE = BASE_URL / ".env"


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


class HDSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, env_prefix="HD_", extra="ignore")
    base_url: str
    admin_api_key: str

    @property
    def endpoint(self) -> str:
        if not self.base_url.startswith("https://"):
            raise ValueError("Не верный helpdesk URL")
        return f"{self.base_url}/sdpapi/request"


class TelegramSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, env_prefix="TELEGRAM_", extra="ignore")
    bot_token: str


class RedisSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, env_prefix="REDIS_", extra="ignore")
    port: int
    host: str
    ttl: int

    @property
    def url(self) -> str:
        return f"redis://{self.host}:{self.port}/0"


@lru_cache
def get_hd_settings() -> HDSettings:
    return HDSettings()


@lru_cache
def get_redis_settings() -> RedisSettings:
    return RedisSettings()


@lru_cache
def get_postgres_settings() -> PostgresSettings:
    return PostgresSettings()
