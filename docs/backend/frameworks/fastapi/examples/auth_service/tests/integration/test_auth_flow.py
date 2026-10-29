import pytest

from tests.integration.conftest import PASSWORD, bearer

pytestmark = pytest.mark.anyio


async def test_register_and_me(client, login):
    response = await client.post('/auth/register', json={'email': 'anna@example.com', 'password': PASSWORD})
    assert response.status_code == 201
    assert response.json()['roles'] == ['user']

    tokens = await login('anna@example.com')
    me = await client.get('/auth/me', headers=bearer(tokens))
    assert me.json()['permissions'] == ['tasks:read', 'tasks:write']


async def test_refresh_token_works_once(client, make_user, login):
    await make_user('anna@example.com')
    tokens = await login('anna@example.com')

    first = await client.post('/auth/refresh', json={'refresh_token': tokens['refresh_token']})
    assert first.status_code == 200
    assert first.json()['refresh_token'] != tokens['refresh_token']

    second = await client.post('/auth/refresh', json={'refresh_token': tokens['refresh_token']})
    assert second.status_code == 401


async def test_reused_refresh_kills_the_whole_session(client, make_user, login):
    await make_user('anna@example.com')
    stolen = await login('anna@example.com')
    fresh = (await client.post('/auth/refresh', json={'refresh_token': stolen['refresh_token']})).json()

    # злоумышленник пробует старый refresh — сессия закрывается для всех
    reuse = await client.post('/auth/refresh', json={'refresh_token': stolen['refresh_token']})
    assert reuse.json()['detail'] == 'Refresh-токен уже использован, сессия завершена'

    assert (await client.post('/auth/refresh', json={'refresh_token': fresh['refresh_token']})).status_code == 401
    assert (await client.get('/auth/me', headers=bearer(fresh))).status_code == 401


async def test_logout_makes_access_token_invalid(client, make_user, login):
    await make_user('anna@example.com')
    tokens = await login('anna@example.com')
    assert (await client.get('/auth/me', headers=bearer(tokens))).status_code == 200

    assert (await client.post('/auth/logout', headers=bearer(tokens))).status_code == 204

    response = await client.get('/auth/me', headers=bearer(tokens))
    assert response.status_code == 401
    assert response.json()['detail'] == 'Токен отозван'
    assert (await client.post('/auth/refresh', json={'refresh_token': tokens['refresh_token']})).status_code == 401


async def test_logout_all_closes_other_devices(client, make_user, login):
    await make_user('anna@example.com')
    phone = await login('anna@example.com', 'phone')
    laptop = await login('anna@example.com', 'laptop')
    assert len((await client.get('/auth/sessions', headers=bearer(laptop))).json()) == 2

    await client.post('/auth/logout/all', headers=bearer(laptop))

    assert (await client.get('/auth/me', headers=bearer(phone))).status_code == 401
    assert (await client.post('/auth/refresh', json={'refresh_token': phone['refresh_token']})).status_code == 401
    # после «выйти везде» новый вход работает
    again = await login('anna@example.com', 'laptop')
    assert (await client.get('/auth/me', headers=bearer(again))).status_code == 200


async def test_password_change_revokes_all_sessions(client, make_user, login):
    await make_user('anna@example.com')
    tokens = await login('anna@example.com')

    response = await client.post(
        '/auth/password', headers=bearer(tokens),
        json={'old_password': PASSWORD, 'new_password': 'new-secret-456'},
    )
    assert response.status_code == 204
    assert (await client.get('/auth/me', headers=bearer(tokens))).status_code == 401
    old = await client.post('/auth/login', json={'email': 'anna@example.com', 'password': PASSWORD})
    assert old.status_code == 401


async def test_role_without_permission_gets_403(client, make_user, login):
    await make_user('anna@example.com', 'user')
    await make_user('boss@example.com', 'manager')

    anna = await login('anna@example.com')
    response = await client.delete('/tasks/1', headers=bearer(anna))
    assert response.status_code == 403
    assert response.json()['detail'] == 'Нужно право tasks:delete'

    boss = await login('boss@example.com')
    assert (await client.delete('/tasks/1', headers=bearer(boss))).status_code == 204


async def test_role_change_applies_without_relogin(client, make_user, login):
    await make_user('admin@example.com', 'admin')
    await make_user('anna@example.com', 'user')
    admin, anna = await login('admin@example.com'), await login('anna@example.com')

    response = await client.put('/users/2/roles/manager', headers=bearer(admin))
    assert response.json()['roles'] == ['manager']

    # права проверяются по базе, а не по роли в токене
    assert (await client.delete('/tasks/1', headers=bearer(anna))).status_code == 204


async def test_login_history_records_user_agent(client, make_user, login):
    await make_user('anna@example.com')
    await client.post('/auth/login', json={'email': 'anna@example.com', 'password': 'wrong-pass'},
                      headers={'User-Agent': 'curl/8.7.1'})
    tokens = await login('anna@example.com', 'Firefox')

    history = (await client.get('/auth/history', headers=bearer(tokens))).json()
    assert [(h['user_agent'], h['success']) for h in history] == [('Firefox', True), ('curl/8.7.1', False)]
