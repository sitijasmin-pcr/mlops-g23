from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    lm_studio_url: str = 'http://127.0.0.1:1234/v1'
    lm_studio_model: str = 'qwen'
    max_tokens: int = 700
    temperature: float = 0.7
    frontend_origin: str = 'http://127.0.0.1:5173'
    model_config = SettingsConfigDict(env_file=Path(__file__).with_name('.env'), extra='ignore')

settings = Settings()
