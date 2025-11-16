from pydantic_settings import BaseSettings

from pydantic import Field


class MongoSettings(BaseSettings):
    """
    Конфигурация для настроек Mongo DB
    """
    host: str = Field(alias='MONGO_HOST', default='127.0.0.1')
    port: int = Field(alias='MONGO_PORT', default=27017)

    @property
    def url(self):
        return f'mongodb://{self.host}:{self.port}'


class JWTSettings(BaseSettings):
    """
    Конфигурация для настроек JWT
    """

    secret_key: str = Field(
        alias='JWT_SECRET_KEY', default='obfismVuOtuo3OEfT6KUhDzsYxrW7ldfc5_WSrv96F8',
    )
    algorithm: str = Field(alias='JWT_ALGORITHM', default='HS256')


class Settings(BaseSettings):
    project_name: str = Field(alias='PROJECT_NAME', default='MyApplication')
    project_description: str = Field(alias='PROJECT_DESCRIPTION', default='Description for MyApplication')
    mongo: MongoSettings = MongoSettings()
    jwt: JWTSettings = JWTSettings()
    default_host: str = '0.0.0.0'
    default_port: int = 8000


settings = Settings()