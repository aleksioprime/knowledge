from pydantic import Field
from pydantic_settings import BaseSettings


class ServiceSettings(BaseSettings):
    host: str = Field(alias='SERVICE_HOST', default='127.0.0.1')
    port: int = Field(alias='SERVICE_PORT', default=8000)

    @property
    def url(self):
        return f'http://{self.host}:{self.port}'


class PostgresSettings(BaseSettings):
    host: str = Field(alias='POSTGRES_HOST', default='127.0.0.1')
    port: int = Field(alias='POSTGRES_PORT', default=5432)
    user: str = Field(alias='POSTGRES_USER', default='admin')
    password: str = Field(alias='POSTGRES_PASSWORD', default='1q2w3e')
    db: str = Field(alias='POSTGRES_DB', default='database')

    @property
    def _base_url(self) -> str:
        return f"{self.user}:{self.password}@{self.host}:{self.port}/{self.db}"

    @property
    def dsn(self) -> str:
        return f"postgresql+asyncpg://{self._base_url}"


class RedisSettings(BaseSettings):
    host: str = Field(alias='REDIS_HOST', default='127.0.0.1')
    port: int = Field(alias='REDIS_PORT', default=6379)


class TestSettings(BaseSettings):
    service: ServiceSettings = ServiceSettings()
    postgres: PostgresSettings = PostgresSettings()
    redis: RedisSettings = RedisSettings()


test_settings = TestSettings()