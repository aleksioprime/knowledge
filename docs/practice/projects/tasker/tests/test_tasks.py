import pytest

pytestmark = pytest.mark.anyio


async def test_create_and_list(client, anna):
    response = await client.post('/tasks', json={'title': 'Купить хлеб', 'due_date': '2026-11-01'}, headers=anna)
    assert response.status_code == 201
    task = response.json()
    assert task['title'] == 'Купить хлеб'
    assert task['done'] is False

    response = await client.get('/tasks', headers=anna)
    assert [t['id'] for t in response.json()] == [task['id']]


async def test_validation(client, anna):
    response = await client.post('/tasks', json={'title': '', 'priority': 10}, headers=anna)
    assert response.status_code == 422
    assert {error['loc'][-1] for error in response.json()['detail']} == {'title', 'priority'}


async def test_partial_update(client, anna):
    task = (await client.post('/tasks', json={'title': 'Сдать отчёт', 'priority': 3}, headers=anna)).json()

    response = await client.patch(f'/tasks/{task["id"]}', json={'done': True}, headers=anna)
    assert response.json()['done'] is True
    assert response.json()['priority'] == 3


async def test_filter_and_pagination(client, anna):
    for i in range(5):
        await client.post('/tasks', json={'title': f'Задача {i}'}, headers=anna)
    await client.patch('/tasks/1', json={'done': True}, headers=anna)

    done = await client.get('/tasks', params={'done': True}, headers=anna)
    assert [t['id'] for t in done.json()] == [1]

    page = await client.get('/tasks', params={'limit': 2, 'offset': 2}, headers=anna)
    assert [t['id'] for t in page.json()] == [3, 4]


async def test_delete(client, anna):
    task = (await client.post('/tasks', json={'title': 'Лишняя'}, headers=anna)).json()

    assert (await client.delete(f'/tasks/{task["id"]}', headers=anna)).status_code == 204
    assert (await client.get(f'/tasks/{task["id"]}', headers=anna)).status_code == 404


async def test_foreign_task_is_hidden(client, anna, boris):
    task = (await client.post('/tasks', json={'title': 'Личное'}, headers=anna)).json()

    response = await client.get(f'/tasks/{task["id"]}', headers=boris)
    assert response.status_code == 404
    assert response.json() == {'detail': 'Задача не найдена'}
