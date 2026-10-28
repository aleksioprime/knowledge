from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """По умолчанию — порты тестового compose на этой машине; в контейнере tests их заменяют переменные окружения."""

    service_url: str = 'http://localhost:28001'
    elastic_url: str = 'http://localhost:29201'
    redis_url: str = 'redis://localhost:26380/0'
    tasks_index: str = 'tasks'


settings = Settings()
