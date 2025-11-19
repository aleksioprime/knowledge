from pydantic import Field
from pydantic_settings import BaseSettings


class ServiceSettings(BaseSettings):
    host: str = Field(alias='SERVICE_HOST', default='127.0.0.1')
    port: int = Field(alias='SERVICE_PORT', default=8000)

    @property
    def url(self):
        return f'http://{self.host}:{self.port}'


class TestSettings(BaseSettings):
    service: ServiceSettings = ServiceSettings()


test_settings = TestSettings()