import backoff
import requests

from tests.functional.core.settings import test_settings


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
    response = requests.get(f"http://{test_settings.service.host}:{test_settings.service.port}/api/ping/health")
    assert response.status_code == 200
