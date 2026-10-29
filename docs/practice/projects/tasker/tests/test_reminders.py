from datetime import date

import pytest

from app.services import reminders

pytestmark = pytest.mark.anyio

TODAY = date(2026, 10, 31)


@pytest.fixture
def sent(monkeypatch):
    letters = []
    monkeypatch.setattr(reminders, 'send_email', lambda to, subject, body: letters.append((to, body)))
    return letters


async def test_remind_about_tasks_due_tomorrow(client, sessions, sent, anna):
    for title, due_date in [('Сдать отчёт', '2026-11-01'), ('Купить хлеб', '2026-11-05'), ('Без срока', None)]:
        await client.post('/tasks', json={'title': title, 'due_date': due_date}, headers=anna)

    async with sessions() as session:
        task_ids = await reminders.find_tasks_to_remind(session, TODAY)
        assert task_ids == [1]
        assert await reminders.send_reminder(session, 1) is True

    assert sent == [('anna@example.com', 'Сдать отчёт')]


async def test_reminder_is_sent_once(client, sessions, sent, anna):
    await client.post('/tasks', json={'title': 'Сдать отчёт', 'due_date': '2026-11-01'}, headers=anna)

    async with sessions() as session:
        assert await reminders.send_reminder(session, 1) is True
        assert await reminders.send_reminder(session, 1) is False
        assert await reminders.find_tasks_to_remind(session, TODAY) == []

    assert len(sent) == 1


async def test_no_reminder_for_done_task(client, sessions, sent, anna):
    await client.post('/tasks', json={'title': 'Сдать отчёт', 'due_date': '2026-11-01'}, headers=anna)
    await client.patch('/tasks/1', json={'done': True}, headers=anna)

    async with sessions() as session:
        assert await reminders.find_tasks_to_remind(session, TODAY) == []

    assert sent == []
