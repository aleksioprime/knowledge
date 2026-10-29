import httpx

BASE_URL = 'http://localhost:8001'

response = httpx.get(f'{BASE_URL}/tasks/42', params={'fields': 'title'})
print(response.status_code, response.json())
print(response.request.url)

response = httpx.post(f'{BASE_URL}/tasks', json={'title': 'Купить хлеб'})
print(response.status_code, response.json())

response = httpx.get(f'{BASE_URL}/tasks/404')
print(response.status_code, response.is_success)
try:
    response.raise_for_status()
except httpx.HTTPStatusError as error:
    print('HTTPStatusError:', error.response.status_code, error.response.json())
