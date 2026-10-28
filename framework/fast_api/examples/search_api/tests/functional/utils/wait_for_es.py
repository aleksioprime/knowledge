"""Ждёт, пока Elasticsearch начнёт отвечать. Нужен, если нечем проверить готовность через healthcheck."""
import random
import time

from elasticsearch import Elasticsearch

from settings import settings


def wait_for_es(timeout: float = 60, start_sleep: float = 0.1, border_sleep: float = 5) -> None:
    client = Elasticsearch(settings.elastic_url)
    deadline = time.monotonic() + timeout
    attempt = 0
    while not client.ping():
        if time.monotonic() > deadline:
            raise TimeoutError(f'Elasticsearch не ответил за {timeout} с')
        time.sleep(random.uniform(0, min(border_sleep, start_sleep * 2 ** attempt)))
        attempt += 1


if __name__ == '__main__':
    wait_for_es()
