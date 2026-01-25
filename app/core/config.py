from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    PROJECT_NAME: str = "Content Orchestrator"
    API_V1_STR: str = "/v1"

    STORAGE_TYPE: str = "local"
    LOCAL_STORAGE_PATH: str = "downloads"
    DATA_PATH: str = "data"

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"

@lru_cache()
def get_settings():
    return Settings()
