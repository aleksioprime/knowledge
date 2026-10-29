from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')

    project_name: str = 'Поиск задач'
    elastic_url: str = 'http://localhost:29200'
    redis_url: str = 'redis://localhost:26379/0'
    tasks_index: str = 'tasks'
    cache_ttl_seconds: int = 60


# Elasticsearch по умолчанию не отдаёт документы дальше 10 000-го (index.max_result_window)
MAX_RESULT_WINDOW = 10_000

settings = Settings()
