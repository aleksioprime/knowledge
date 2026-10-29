import pytest

from testdata.tasks import make_task


@pytest.fixture
async def search_data(es_write_data) -> None:
    reports = [make_task(n, title=f'Подготовить отчёт №{n}', tags=['работа']) for n in range(30)]
    shopping = [make_task(100 + n, title=f'Купить продукты №{n}', tags=['дом']) for n in range(20)]
    in_description = [make_task(200, title='Встреча с командой', description='Обсудить квартальные отчёты')]
    await es_write_data(reports + shopping + in_description)


@pytest.mark.parametrize(
    ('params', 'expected_count'),
    [
        ({'query': 'отчёты'}, 31),  # 30 в названии + 1 в описании; «отчёт» и «отчёты» — одна основа
        ({'query': 'продукты'}, 20),
        ({'query': 'отчёт', 'page_size': 10}, 10),
        ({'query': 'отчёт', 'page_size': 10, 'page_number': 4}, 1),
        ({'query': 'отчёт', 'page_size': 10, 'page_number': 5}, 0),
        ({'query': 'несуществующее'}, 0),
    ],
)
async def test_search(http_client, search_data, params, expected_count):
    response = await http_client.get('/api/v1/tasks/search', params=params)

    assert response.status_code == 200
    assert len(response.json()) == expected_count


@pytest.mark.parametrize(
    'params',
    [
        {},
        {'query': ''},
        {'query': 'отчёт', 'page_size': 0},
        {'query': 'отчёт', 'page_size': 101},
        {'query': 'отчёт', 'page_number': 0},
        {'query': 'отчёт', 'page_number': 'первая'},
        {'query': 'отчёт', 'page_number': 101, 'page_size': 100},  # за пределами max_result_window
    ],
)
async def test_search_validation(http_client, params):
    response = await http_client.get('/api/v1/tasks/search', params=params)

    assert response.status_code == 422
