from pydantic_settings import BaseSettings

from pydantic import Field


class DBSettings(BaseSettings):
    """
    Конфигурация для настроек базы данных
    """
    name: str = Field(alias='DB_NAME', default='database')
    user: str = Field(alias='DB_USER', default='admin')
    password: str = Field(alias='DB_PASSWORD', default='123qwe')
    host: str = Field(alias='DB_HOST', default='127.0.0.1')
    port: int = Field(alias='DB_PORT', default=5432)
    show_query: bool = Field(alias='SHOW_SQL_QUERY', default=False)

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
    """
    secret_key: str = Field(
        alias='JWT_SECRET_KEY',
        default='7Fp0SZsBRKqo1K82pnQ2tcXV9XUfuiIJxpDcE5FofP2fL0vlZw3SOkI3YYLpIGP',
    )
    algorithm: str = Field(alias='JWT_ALGORITHM', default='HS256')
    access_token_expire_time: timedelta = Field(default=timedelta(minutes=15))
    refresh_token_expire_time: timedelta = Field(default=timedelta(days=10))


class Settings(BaseSettings):
    project_name: str = Field(alias="PROJECT_NAME", default="HyperSpectRus")
    project_description: str = Field(
        alias="PROJECT_DESCRIPTION", default="Application for HyperSpectRus"
    )
    jwt: JWTSettings = JWTSettings()
    db: DBSettings = DBSettings()

    default_host: str = "0.0.0.0"
    default_port: int = 8000

    timezone: str = Field(alias="TIMEZONE", default="Europe/Moscow")

settings = Settings()