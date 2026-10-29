from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')

    database_url: str = 'postgresql+asyncpg://auth:auth@localhost:45432/auth'
    redis_url: str = 'redis://localhost:46379/0'
    secret_key: str = 'dev-only-insecure-key-change-me-32b'
    access_ttl_minutes: int = 15
    refresh_ttl_days: int = 30


settings = Settings()
