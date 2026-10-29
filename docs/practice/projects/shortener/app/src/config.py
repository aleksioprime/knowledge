from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')

    database_url: str = 'postgresql+asyncpg://shortener:shortener@localhost:5433/shortener'
    redis_url: str = 'redis://localhost:6380/0'
    base_url: str = 'http://localhost:8001'
    cache_ttl_seconds: int = 24 * 60 * 60


settings = Settings()
