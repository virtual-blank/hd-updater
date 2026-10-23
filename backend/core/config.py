from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path
from functools import lru_cache

BASE_URL = Path(__file__).resolve().parent.parent.parent
ENV_FILE = BASE_URL / ".env"


class HDSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, env_prefix="HD_", extra="ignore")
    api_key: str


@lru_cache
def get_hd_settings() -> HDSettings:
    return HDSettings()
