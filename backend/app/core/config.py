from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    API_TITLE: str = "Cosmos API"
    API_ORIGINS: str = "*"
    DB_DSN: str | None = None

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()