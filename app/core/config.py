from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Telegram
    bot_token: str
    webhook_url: str
    webhook_path: str = "/telegram/webhook"

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@db:5432/docservice"

    # Grouping
    group_timeout_minutes: int = 10
    group_check_interval_seconds: int = 60  # как часто проверять группы на закрытие

    # Storage
    storage_path: str = "/app/storage"


settings = Settings()
