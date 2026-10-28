from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')

    database_url: str = 'postgresql+asyncpg://tasker:tasker@localhost:5432/tasker'
    secret_key: str = 'change-me'
    access_token_expire_minutes: int = 60


settings = Settings()
