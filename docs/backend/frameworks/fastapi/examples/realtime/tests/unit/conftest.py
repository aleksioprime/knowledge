import fakeredis
import pytest
from fakeredis.aioredis import FakeRedis
from fastapi.testclient import TestClient

from app.auth import create_token
from app.config import Settings
from app.main import create_app

SETTINGS = Settings(messages_per_second=1, messages_burst=3, max_message_bytes=256, auth_timeout=1)


@pytest.fixture
def server():
    return fakeredis.FakeServer()


def make_client(server, instance: str) -> TestClient:
    redis = FakeRedis(server=server, decode_responses=True)
    settings = Settings(**{**SETTINGS.__dict__, 'instance': instance})
    return TestClient(create_app(settings, redis))


@pytest.fixture
def client(server):
    with make_client(server, 'app1') as client:
        yield client


@pytest.fixture
def token():
    return create_token('anna', SETTINGS.jwt_secret)
