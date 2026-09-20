from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    database_url: str = (
        "postgresql+asyncpg://ledgermap:ledgermap@localhost:5432/ledgermap"
    )
    log_level: str = "INFO"

    # Off by default: the classifier needs a real taxonomy and an API key
    # (ANTHROPIC_API_KEY, read directly by the anthropic SDK) to do anything
    # useful. See ledgermap.integrations.llm for the provider-agnostic
    # interface this flag gates.
    llm_classification_enabled: bool = False

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()