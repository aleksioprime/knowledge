from app.bus import is_newer


def test_poll_returns_missed(client, token):
    ids = [client.post('/notify', json={'user_id': 'anna', 'event': 'comment_added', 'data': {'n': n}}).json()['id']
           for n in range(3)]
    response = client.get('/poll', params={'token': token, 'after': ids[0]})
    assert [item['data']['n'] for item in response.json()['items']] == [1, 2]


def test_poll_timeout_returns_empty(client, token):
    response = client.get('/poll', params={'token': token, 'timeout': 0.2})
    assert response.json() == {'items': []}


def test_sse_requires_token(client):
    assert client.get('/events', params={'token': 'broken'}).status_code == 401


def test_stream_ids_compare_as_numbers():
    assert is_newer('1761730000000-10', '1761730000000-9')
    assert not is_newer('1761730000000-0', '1761730000001-0')
