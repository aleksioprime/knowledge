import httpx

try:
    httpx.get('http://localhost:8001/slow', timeout=1.0)
except httpx.TimeoutException as error:
    print(type(error).__name__, error)

try:
    httpx.get('http://localhost:9999/tasks/1')
except httpx.ConnectError as error:
    print(type(error).__name__, error)

timeout = httpx.Timeout(10.0, connect=2.0)
print(timeout)
