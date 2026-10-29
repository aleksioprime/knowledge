import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    redis_url: str = 'redis://localhost:46379/0'
    instance: str = 'local'
    jwt_secret: str = 'dev-secret-change-me-at-least-32-bytes'
    allowed_origins: tuple[str, ...] = ('http://localhost:5173',)
    auth_timeout: float = 5.0
    messages_per_second: float = 5.0
    messages_burst: int = 10
    max_message_bytes: int = 4096
    send_timeout: float = 2.0
    sse_queue_size: int = 100
    stream_maxlen: int = 1000


def get_settings() -> Settings:
    return Settings(
        redis_url=os.getenv('REDIS_URL', Settings.redis_url),
        instance=os.getenv('INSTANCE', Settings.instance),
        jwt_secret=os.getenv('JWT_SECRET', Settings.jwt_secret),
        allowed_origins=tuple(os.getenv('ALLOWED_ORIGINS', ','.join(Settings.allowed_origins)).split(',')),
    )
