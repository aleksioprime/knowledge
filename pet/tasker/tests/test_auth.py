import pytest

pytestmark = pytest.mark.anyio


async def test_register_and_me(client, anna):
    response = await client.get('/auth/me', headers=anna)
    assert response.status_code == 200
    assert response.json()['email'] == 'anna@example.com'


async def test_register_twice(client, anna):
    response = await client.post('/auth/register', json={'email': 'anna@example.com', 'password': 'secret123'})
    assert response.status_code == 409


async def test_wrong_password(client, anna):
    response = await client.post('/auth/token', data={'username': 'anna@example.com', 'password': 'wrong'})
    assert response.status_code == 401


async def test_without_token(client):
    response = await client.get('/tasks')
    assert response.status_code == 401
