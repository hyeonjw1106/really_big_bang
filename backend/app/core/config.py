from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    API_TITLE: str = "Cosmos API"
    API_ORIGINS: str = "*"
    DB_DSN: str | None = None
    DATA_DIR: str = "data"
    BLENDER_BIN: str = "blender"  # 시스템에 설치된 블렌더 실행 파일 경로

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()
