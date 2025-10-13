from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    API_TITLE: str = "Cosmos API"
    API_ORIGINS: str = "*"

    class Config:
        env_file = ".env"

settings = Settings()