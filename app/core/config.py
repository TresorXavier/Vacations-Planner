from pathlib import Path
from pydantic import ConfigDict
from pydantic_settings import BaseSettings
BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    ANTHROPIC_API_KEY: str
    DATA_BASE_URL: str
    TOKEN_EXPIRE_MINUTES:int
    SECRET_KEY:str
    ALGORITHM:str
    MODEL_NAME:str
    MAX_TOKEN:int
    TEMPERATURE:float
    UNSTRUCTURED_API:str
    WIKI_API_BASE :str
    USER_AGENT:str
    model_config = ConfigDict( env_file=BASE_DIR / ".env",env_file_encoding="utf-8")


settings = Settings()