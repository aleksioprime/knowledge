"""Прогон сценариев против запущенных API и воркера.

    python check.py
"""

import asyncio
import json
import subprocess
import sys
import time
import uuid
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import aio_pika
import asyncpg
import httpx
from aio_pika.exceptions import DeliveryError

from common import DATABASE_URL, DLQ, EXCHANGE, MAX_ATTEMPTS, RABBIT_URL, retry_queue

API = 'http://localhost:48000'
MAILPIT = 'http://localhost:48026/api/v1'
COMPOSE = ['docker', 'compose', '-p', 'kb-notify']
SCHEDULER = [sys.executable, 'scheduler.py']

http = httpx.Client(timeout=10)


def title(text: str) -> None:
    print(f'\n=== {text}')


def zone_with_local_hour(hours: range) -> str:
    """Часовой пояс, в котором сейчас местное время попадает в hours."""
    now = datetime.now(UTC)
    for offset in range(-12, 15):
        name = f'Etc/GMT{-offset:+d}' if offset else 'Etc/GMT'
        if now.astimezone(ZoneInfo(name)).hour in hours:
            return name
    raise RuntimeError('не нашёл подходящий пояс')


def mails() -> list[dict]:
    try:
        return http.get(f'{MAILPIT}/messages').json()['messages']
    except httpx.TransportError:
        return []  # Mailpit ещё поднимается


def show_mails() -> None:
    items = mails()
    print(f'писем в Mailpit: {len(items)}')
    for m in sorted(items, key=lambda m: m['To'][0]['Address']):
        print(f"  {m['To'][0]['Address']:<18} {m['Subject']}")


def wait_mails(count: int, timeout: float = 30) -> None:
    for _ in range(int(timeout * 2)):
        if len(mails()) >= count:
            time.sleep(1)  # письмо уже в Mailpit, а статус sent фиксируется следом
            return
        time.sleep(0.5)


async def queue_size(name: str) -> int:
    connection = await aio_pika.connect_robust(RABBIT_URL)
    async with connection:
        channel = await connection.channel()
        queue = await channel.declare_queue(name, passive=True)
        return queue.declaration_result.message_count


def send(event_type: str, data: dict, event_id: str | None = None) -> str:
    event_id = event_id or str(uuid.uuid4())
    response = http.post(f'{API}/events', json={
        'event_id': event_id,
        'type': event_type,
        'occurred_at': datetime.now(UTC).isoformat(),
        'data': data,
    })
    print(f'POST /events {event_type} → {response.status_code}')
    return event_id


async def sql(query: str, *args):
    db = await asyncpg.connect(DATABASE_URL)
    try:
        return await db.fetch(query, *args)
    finally:
        await db.close()


def statuses(prefix: str) -> None:
    rows = asyncio.run(sql(
        """SELECT notification_id, status, reason, send_after FROM notify.notifications
           WHERE notification_id LIKE $1 ORDER BY notification_id""", prefix + '%',
    ))
    for r in rows:
        line = f"  {r['notification_id'][-30:]:<30} {r['status']}"
        if r['reason']:
            line += f" ({r['reason']})"
        if r['send_after']:
            line += f" до {r['send_after']:%H:%M} UTC"
        print(line)


async def publish_raw(body: bytes, key: str, message_id: str) -> None:
    connection = await aio_pika.connect_robust(RABBIT_URL)
    async with connection:
        channel = await connection.channel(publisher_confirms=True, on_return_raises=True)
        exchange = await channel.get_exchange(EXCHANGE)
        await exchange.publish(
            aio_pika.Message(body, message_id=message_id, delivery_mode=aio_pika.DeliveryMode.PERSISTENT),
            routing_key=key, mandatory=True,
        )


async def read_dlq() -> list[aio_pika.abc.AbstractIncomingMessage]:
    connection = await aio_pika.connect_robust(RABBIT_URL)
    async with connection:
        channel = await connection.channel()
        queue = await channel.get_queue(DLQ)
        result = []
        while message := await queue.get(fail=False):
            result.append(message)
            await message.ack()
        return result


async def purge_queues() -> None:
    connection = await aio_pika.connect_robust(RABBIT_URL)
    async with connection:
        channel = await connection.channel()
        for name in [DLQ, *(retry_queue(i) for i in range(1, MAX_ATTEMPTS))]:
            await (await channel.get_queue(name)).purge()


def reset() -> None:
    asyncio.run(purge_queues())
    day = zone_with_local_hour(range(10, 19))
    asyncio.run(sql('TRUNCATE notify.notifications, notify.scheduler_runs'))
    asyncio.run(sql('UPDATE notify.user_settings SET timezone = $1', day))
    http.delete(f'{MAILPIT}/messages')
    print(f'очереди, база и Mailpit очищены, у всех пользователей пояс {day} (сейчас день)')


def scenario_1() -> None:
    title('1. Событие → письмо')
    event_id = send('task.assigned', {'task_id': 1, 'assignee_id': 2, 'actor_id': 1})
    wait_mails(1)
    show_mails()
    statuses(event_id)


def scenario_2() -> None:
    title('2. Одно событие дважды → одно письмо')
    http.delete(f'{MAILPIT}/messages')
    event_id = str(uuid.uuid4())
    send('task.assigned', {'task_id': 2, 'assignee_id': 3, 'actor_id': 2}, event_id)
    send('task.assigned', {'task_id': 2, 'assignee_id': 3, 'actor_id': 2}, event_id)
    time.sleep(3)
    show_mails()
    statuses(event_id)


def scenario_3() -> None:
    title('3. SMTP недоступен → retry, после возврата письмо доставлено')
    http.delete(f'{MAILPIT}/messages')
    subprocess.run([*COMPOSE, 'stop', 'mailpit'], check=True, capture_output=True)
    print('mailpit остановлен')
    send('comment.created', {'task_id': 1, 'comment_id': 1, 'author_id': 1})
    time.sleep(5)
    print('прошло 5 с: попытки идут через retry-очереди, см. лог воркера')
    subprocess.run([*COMPOSE, 'start', 'mailpit'], check=True, capture_output=True)
    print('mailpit запущен')
    wait_mails(1)
    show_mails()

    title('3б. «Битые» сообщения → DLQ')
    asyncio.run(publish_raw(b'{not json', 'task.v1.assigned', 'garbage-1'))
    print('опубликован не-JSON (мимо API)')
    asyncio.run(publish_raw(
        json.dumps({'event_id': 'missing-task-1', 'type': 'task.assigned',
                    'data': {'task_id': 999, 'assignee_id': 2, 'actor_id': 1}}).encode(),
        'task.v1.assigned', 'missing-task-1',
    ))
    print('опубликовано событие о несуществующей задаче 999 (мимо API)')
    for _ in range(40):
        if asyncio.run(queue_size(DLQ)) >= 2:
            break
        time.sleep(1)
    for message in asyncio.run(read_dlq()):
        headers = message.headers or {}
        print(f"  DLQ: {message.message_id:<15} попытка {headers.get('x-attempt')}, {headers.get('x-error')}")


def scenario_4() -> None:
    title('4а. Отписка от категории')
    http.delete(f'{MAILPIT}/messages')
    event_id = send('comment.created', {'task_id': 2, 'comment_id': 2, 'author_id': 1})
    time.sleep(3)
    show_mails()
    statuses(event_id)

    title('4б. Неактуальное событие: задача уже закрыта')
    event_id = send('task.assigned', {'task_id': 4, 'assignee_id': 2, 'actor_id': 1})
    time.sleep(2)
    statuses(event_id)

    title('4в. Тихие часы → отложено, утром отправлено')
    http.delete(f'{MAILPIT}/messages')
    night = zone_with_local_hour(range(0, 6))
    asyncio.run(sql('UPDATE notify.user_settings SET timezone = $1 WHERE user_id = 4', night))
    print(f'у Глеба пояс {night}, там сейчас ночь')
    event_id = send('task.assigned', {'task_id': 3, 'assignee_id': 4, 'actor_id': 1})
    time.sleep(3)
    show_mails()
    statuses(event_id)
    print('$ python scheduler.py release --all   # «наступило утро»')
    print(subprocess.run([*SCHEDULER, 'release', '--all'], capture_output=True, text=True).stdout, end='')
    wait_mails(1)
    show_mails()
    statuses(event_id)


def scenario_5() -> None:
    title('5. Планировщик дважды за период → один дайджест')
    http.delete(f'{MAILPIT}/messages')
    day = zone_with_local_hour(range(10, 19))
    asyncio.run(sql('UPDATE notify.user_settings SET timezone = $1', day))
    for args in (['digest'], ['digest'], ['digest', '--force']):
        print('$ python scheduler.py ' + ' '.join(args))
        print(subprocess.run([*SCHEDULER, *args], capture_output=True, text=True).stdout, end='')
    time.sleep(4)
    show_mails()
    statuses('digest:')


def scenario_6() -> None:
    title('6. Публикация, которую некуда доставить (mandatory)')
    try:
        asyncio.run(publish_raw(b'{}', 'payment.created', 'nobody-listens'))
    except DeliveryError as exc:
        print(f'брокер вернул сообщение: {exc!r}')
    else:
        print('сообщение принято')


if __name__ == '__main__':
    reset()
    scenario_1()
    scenario_2()
    scenario_3()
    scenario_4()
    scenario_5()
    scenario_6()
