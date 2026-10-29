import time

import httpx

# Встроенные повторы транспорта касаются только ошибок соединения
transport = httpx.HTTPTransport(retries=3)
with httpx.Client(transport=transport) as client:
    try:
        client.get('http://localhost:9999/tasks/1')
    except httpx.ConnectError as error:
        print('после 3 повторов:', type(error).__name__)

RETRY_STATUSES = {502, 503, 504}


def get_with_retries(client: httpx.Client, url: str, attempts: int = 4) -> httpx.Response:
    for attempt in range(1, attempts + 1):
        try:
            response = client.get(url)
            if response.status_code not in RETRY_STATUSES:
                return response
            print(f'попытка {attempt}: {response.status_code}')
        except httpx.TransportError as error:
            print(f'попытка {attempt}: {type(error).__name__}')
        if attempt < attempts:
            time.sleep(0.2 * 2 ** (attempt - 1))
    response.raise_for_status()
    return response


with httpx.Client(base_url='http://localhost:8001', timeout=5.0) as client:
    print(get_with_retries(client, '/flaky').json())
