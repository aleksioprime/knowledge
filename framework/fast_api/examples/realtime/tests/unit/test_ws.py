import pytest
from starlette.websockets import WebSocketDisconnect

from app.auth import create_token
from tests.unit.conftest import make_client


def notify(client, user_id='anna', event='task_assigned', **data):
    response = client.post('/notify', json={'user_id': user_id, 'event': event, 'data': data})
    assert response.status_code == 202
    return response.json()['id']


def test_notification_reaches_every_tab(client, token):
    with client.websocket_connect(f'/ws?token={token}') as tab1, \
            client.websocket_connect(f'/ws?token={token}') as tab2:
        assert tab1.receive_json()['type'] == 'hello'
        assert tab2.receive_json()['type'] == 'hello'
        event_id = notify(client, task_id=42, title='Подготовить отчёт')
        for tab in (tab1, tab2):
            message = tab.receive_json()
            assert message['id'] == event_id
            assert message['data'] == {'task_id': 42, 'title': 'Подготовить отчёт'}


def test_other_user_does_not_receive(client, token):
    with client.websocket_connect(f'/ws?token={token}') as anna:
        anna.receive_json()
        notify(client, user_id='boris')
        anna.send_json({'type': 'ping'})
        assert anna.receive_json() == {'type': 'pong'}


def test_two_instances_share_bus(server, token):
    with make_client(server, 'app1') as app1, make_client(server, 'app2') as app2:
        with app1.websocket_connect(f'/ws?token={token}') as ws:
            ws.receive_json()
            notify(app2, comment='Посмотри правки')
            message = ws.receive_json()
            assert message['from'] == 'app2'
            assert message['data'] == {'comment': 'Посмотри правки'}


def test_token_in_first_message(client, token):
    with client.websocket_connect('/ws') as ws:
        ws.send_json({'type': 'auth', 'token': token})
        assert ws.receive_json()['user_id'] == 'anna'


@pytest.mark.parametrize('url', ['/ws?token=broken', '/ws'])
def test_invalid_token_closes_with_1008(client, url):
    with client.websocket_connect(url) as ws:
        if url == '/ws':
            ws.send_json({'type': 'auth', 'token': 'broken'})
        with pytest.raises(WebSocketDisconnect) as error:
            ws.receive_json()
    assert error.value.code == 1008


def test_foreign_origin_rejected(client, token):
    with pytest.raises(WebSocketDisconnect) as error:
        with client.websocket_connect(f'/ws?token={token}', headers={'origin': 'https://evil.example'}):
            pass
    assert error.value.code == 1008


def test_disconnect_removes_connection(client, token):
    with client.websocket_connect(f'/ws?token={token}') as ws:
        ws.receive_json()
        assert client.get('/debug/connections').json()['websocket'] == {'anna': 1}
    assert client.get('/debug/connections').json()['websocket'] == {}


def test_flood_closes_connection(client, token):
    with client.websocket_connect(f'/ws?token={token}') as ws:
        ws.receive_json()
        with pytest.raises(WebSocketDisconnect) as error:
            for _ in range(10):
                ws.send_json({'type': 'ping'})
                ws.receive_json()
    assert error.value.code == 1008
    assert error.value.reason == 'too many messages'


def test_big_message_closes_with_1009(client, token):
    with client.websocket_connect(f'/ws?token={token}') as ws:
        ws.receive_json()
        ws.send_text('x' * 1000)
        with pytest.raises(WebSocketDisconnect) as error:
            ws.receive_json()
    assert error.value.code == 1009


def test_missed_notifications_by_last_id(client, token):
    first = notify(client, task_id=1)
    notify(client, task_id=2)
    notify(client, task_id=3)
    with client.websocket_connect(f'/ws?token={token}&last_id={first}') as ws:
        ws.receive_json()
        assert [ws.receive_json()['data']['task_id'] for _ in range(2)] == [2, 3]
