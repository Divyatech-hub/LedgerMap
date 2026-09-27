from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    database_url: str = (
        "postgresql+asyncpg://ledgermap:ledgermap@localhost:5432/ledgermap"
    )
    log_level: str = "INFO"

    # Off by default: the classifier needs a real taxonomy and Google Cloud
    # credentials to do anything useful. See ledgermap.integrations.llm for
    # the provider-agnostic interface this flag gates.
    llm_classification_enabled: bool = False

    # Gemini runs on the Gemini Enterprise Agent Platform (previously Vertex
    # AI) and authenticates with Application Default Credentials, so there
    # is no API key here. None lets the SDK fall back to the
    # GOOGLE_CLOUD_PROJECT / GOOGLE_CLOUD_LOCATION environment variables.
    google_cloud_project: str | None = None
    google_cloud_location: str = "global"
    gemini_model: str = "gemini-3.5-flash-lite"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()