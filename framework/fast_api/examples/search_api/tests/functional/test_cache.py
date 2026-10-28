from settings import settings
from testdata.tasks import make_task


async def test_search_is_cached(http_client, es_client, es_write_data):
    task = make_task(1, title='Подготовить отчёт')
    await es_write_data([task])
    first = await http_client.get('/api/v1/tasks/search', params={'query': 'отчёт'})

    # Удаляем документ в обход сервиса: если ответ не изменился, он пришёл из Redis
    await es_client.delete(index=settings.tasks_index, id=task['id'], refresh=True)
    second = await http_client.get('/api/v1/tasks/search', params={'query': 'отчёт'})

    assert len(first.json()) == 1
    assert second.json() == first.json()


async def test_cache_key_depends_on_all_params(http_client, es_client, es_write_data):
    task = make_task(1, title='Подготовить отчёт')
    await es_write_data([task])
    await http_client.get('/api/v1/tasks/search', params={'query': 'отчёт'})

    await es_client.delete(index=settings.tasks_index, id=task['id'], refresh=True)
    other_page_size = await http_client.get('/api/v1/tasks/search', params={'query': 'отчёт', 'page_size': 10})

    assert other_page_size.json() == []


async def test_task_details_are_cached(http_client, es_client, es_write_data):
    task = make_task(1)
    await es_write_data([task])
    first = await http_client.get(f'/api/v1/tasks/{task["id"]}')

    await es_client.delete(index=settings.tasks_index, id=task['id'], refresh=True)
    second = await http_client.get(f'/api/v1/tasks/{task["id"]}')

    assert second.status_code == 200
    assert second.json() == first.json()
