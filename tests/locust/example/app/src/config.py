from pydantic_settings import BaseSettings
from pydantic import Field
from datetime import timedelta


class DBSettings(BaseSettings):
    """
    Конфигурация для настроек базы данных
    """
    name: str = Field(alias='DB_NAME', default='database')
    user: str = Field(alias='DB_USER', default='admin')
    password: str = Field(alias='DB_PASSWORD', default='123qwe')
    host: str = Field(alias='DB_HOST', default='127.0.0.1')
    port: int = Field(alias='DB_PORT', default=5432)

    @property
    def _base_url(self) -> str:
        """ Формирует базовый URL для подключения к базе данных """
        return f"{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"

    @property
    def dsn(self) -> str:
        """ Формирует DSN строку для подключения к базе данных с использованием asyncpg """
        return f"postgresql+asyncpg://{self._base_url}"


class JWTSettings(BaseSettings):
    """
    Конфигурация для настроек JWT
    Секретный ключ можно сгенерировать командой:
    python3 -c "import secrets; print(secrets.token_hex(32))"
    """
    secret_key: str = Field(
        alias='JWT_SECRET_KEY',
        default='c2a3c3c8bd802a7eb095976f717138cfd26841ad63b6a7feeb20aacc8c706c60',
    )
    algorithm: str = Field(alias='JWT_ALGORITHM', default='HS256')
    access_token_expire_time: timedelta = Field(default=timedelta(minutes=15))
    refresh_token_expire_time: timedelta = Field(default=timedelta(days=10))


class Settings(BaseSettings):
    """
    Основные настройки приложения
    """
    # Настройки проекта
    PROJECT_NAME: str = "Locust Test API"
    API_PREFIX: str = "/api"

    # Вложенные настройки
    jwt: JWTSettings = JWTSettings()
    db: DBSettings = DBSettings()


settings = Settings()