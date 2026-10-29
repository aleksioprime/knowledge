import uuid

from testdata.tasks import make_task


async def test_get_task(http_client, es_write_data):
    task = make_task(1, title='Купить хлеб', tags=['дом'])
    await es_write_data([task])

    response = await http_client.get(f'/api/v1/tasks/{task["id"]}')

    assert response.status_code == 200
    body = response.json()
    assert body['id'] == task['id']
    assert body['title'] == 'Купить хлеб'
    assert body['tags'] == ['дом']


async def test_get_task_not_found(http_client):
    response = await http_client.get(f'/api/v1/tasks/{uuid.uuid4()}')

    assert response.status_code == 404
    assert response.json() == {'detail': 'Задача не найдена'}


async def test_get_task_invalid_id(http_client):
    response = await http_client.get('/api/v1/tasks/not-a-uuid')

    assert response.status_code == 422


async def test_list_by_tag_sorted_by_modified(http_client, es_write_data):
    await es_write_data([
        make_task(1, tags=['работа']),
        make_task(3, tags=['работа', 'срочно']),
        make_task(2, tags=['дом']),
        make_task(4, tags=['работа']),
    ])

    newest_first = await http_client.get('/api/v1/tasks/', params={'tag': 'работа'})
    oldest_first = await http_client.get('/api/v1/tasks/', params={'tag': 'работа', 'sort': 'modified'})

    assert [task['title'] for task in newest_first.json()] == ['Задача №4', 'Задача №3', 'Задача №1']
    assert [task['title'] for task in oldest_first.json()] == ['Задача №1', 'Задача №3', 'Задача №4']


async def test_list_invalid_sort(http_client):
    response = await http_client.get('/api/v1/tasks/', params={'sort': 'title'})

    assert response.status_code == 422
