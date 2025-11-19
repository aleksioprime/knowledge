import backoff
import psycopg2
import redis
import requests

from tests.functional.core.settings import test_settings


@backoff.on_exception(
    backoff.expo,
    psycopg2.OperationalError,
    max_tries=10,
    max_time=100,
    jitter=backoff.full_jitter,
    on_backoff=lambda details: print(f"Retrying connection to PostgreSQL: {details}")
)
def wait_for_postgres():
    """
    Ждёт доступность PostgreSQL
    """
    try:
        conn = psycopg2.connect(
            dbname=test_settings.postgres.db,
            user=test_settings.postgres.user,
            password=test_settings.postgres.password,
            host=test_settings.postgres.host,
            port=test_settings.postgres.port,
        )
        conn.close()
    except psycopg2.OperationalError as e:
        raise psycopg2.OperationalError("PostgreSQL is not available") from e


@backoff.on_exception(
    backoff.expo,
    redis.redis_exceptions.ConnectionError,
    max_tries=10,
    max_time=100,
    jitter=backoff.full_jitter
)
def wait_for_redis():
    """
    Ждёт доступность Redis
    """
    redis_client = redis.Redis(host=test_settings.redis.host, port=test_settings.redis.port)
    if not redis_client.ping():
        raise redis.redis_exceptions.ConnectionError("Redis is not available")


@backoff.on_exception(
    backoff.expo,
    Exception,
    max_tries=10,
    max_time=100,
    jitter=backoff.full_jitter,
    on_backoff=lambda details: print(f"Retrying connection to FastAPI: {details}")
)
def wait_for_app():
    """
    Ждёт доступности приложения
    """
    response = requests.get(f"http://{test_settings.service.host}:{test_settings.service.port}/api/ping/")
    assert response.status_code == 200


if __name__ == '__main__':
    wait_for_postgres()
    print("PostgreSQL is ready!")

    wait_for_redis()
    print("Redis is ready!")

    wait_for_app()
    print("FastAPI app is ready!")
