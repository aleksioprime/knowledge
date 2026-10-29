"""Воркер email: обогащает событие, проверяет подписки и тихие часы, отправляет письмо.

Ошибки обрабатывает так:
- сообщение не разобрать → сразу в DLQ, повторять бесполезно;
- любая другая ошибка → в retry-очередь со своей задержкой, после MAX_ATTEMPTS → в DLQ.
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, time, timedelta
from email.message import EmailMessage
from zoneinfo import ZoneInfo

import aio_pika
import aiosmtplib
import asyncpg
from jinja2 import StrictUndefined
from jinja2.sandbox import SandboxedEnvironment

from common import (
    DATABASE_URL, DLQ, EVENT_TYPES, MAX_ATTEMPTS, QUEUE, RABBIT_URL,
    SMTP_HOST, SMTP_PORT, declare_topology, retry_queue,
)

PREFETCH = 10
SMTP_RATE_PER_SECOND = 20

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s', datefmt='%H:%M:%S')
log = logging.getLogger('worker')
jinja = SandboxedEnvironment(undefined=StrictUndefined)


class BadMessage(Exception):
    """Сообщение нельзя обработать никогда: повторы не помогут."""


@dataclass
class Delivery:
    user_id: int
    context: dict = field(default_factory=dict)
    skip_reason: str | None = None


class RateLimiter:
    """Не больше per_second отправок в секунду на весь воркер."""

    def __init__(self, per_second: float):
        self.interval = 1 / per_second
        self.next_slot = 0.0
        self.lock = asyncio.Lock()

    async def wait(self) -> None:
        loop = asyncio.get_running_loop()
        async with self.lock:
            now = loop.time()
            delay = self.next_slot - now
            self.next_slot = max(now, self.next_slot) + self.interval
        if delay > 0:
            await asyncio.sleep(delay)


smtp_limiter = RateLimiter(SMTP_RATE_PER_SECOND)


def quiet_until(now: datetime, tz: str, start: time, end: time) -> datetime | None:
    """Если у пользователя сейчас тихие часы — вернуть, когда они закончатся (UTC)."""
    local = now.astimezone(ZoneInfo(tz))
    t = local.time()
    is_quiet = (t >= start or t < end) if start > end else (start <= t < end)
    if not is_quiet:
        return None
    morning = local.replace(hour=end.hour, minute=end.minute, second=0, microsecond=0)
    if morning <= local:
        morning += timedelta(days=1)
    return morning.astimezone(UTC)


async def build_deliveries(db: asyncpg.Connection, event: dict) -> list[Delivery]:
    """Кому писать и что подставить в шаблон. Источник прислал только id — данные берём сами."""
    data = event['data']
    if event['type'] == 'task.assigned':
        task = await db.fetchrow('SELECT * FROM tasker.tasks WHERE id = $1', data['task_id'])
        if task is None:
            raise LookupError(f"задача {data['task_id']} не найдена")
        delivery = Delivery(data['assignee_id'], {'task': dict(task)})
        # Проверка актуальности: пока событие шло, задачу могли закрыть или переназначить
        if task['status'] == 'done' or task['assignee_id'] != data['assignee_id']:
            delivery.skip_reason = 'неактуально'
        return [delivery]

    if event['type'] == 'comment.created':
        task = await db.fetchrow('SELECT * FROM tasker.tasks WHERE id = $1', data['task_id'])
        comment = await db.fetchrow('SELECT * FROM tasker.comments WHERE id = $1', data['comment_id'])
        if task is None or comment is None:
            raise LookupError('задача или комментарий не найдены')
        author = await db.fetchrow('SELECT name FROM tasker.users WHERE id = $1', data['author_id'])
        recipients = {task['author_id'], task['assignee_id']} - {data['author_id'], None}
        context = {'task': dict(task), 'comment': dict(comment), 'author': dict(author)}
        return [Delivery(user_id, context) for user_id in sorted(recipients)]

    if event['type'] == 'digest.weekly':
        # Планировщик уже собрал данные пачкой, ничего не догружаем
        return [Delivery(data['user_id'], {'period': data['period'], 'tasks': data['tasks']})]

    raise BadMessage(f"неизвестный тип {event['type']}")


async def deliver(pool: asyncpg.Pool, event: dict, delivery: Delivery, released: bool) -> str:
    category = EVENT_TYPES[event['type']]['category']
    notification_id = f"{event['event_id']}:{delivery.user_id}:email"

    async with pool.acquire() as db, db.transaction():
        await db.execute(
            """INSERT INTO notify.notifications (notification_id, user_id, channel, category, status)
               VALUES ($1, $2, 'email', $3, 'pending') ON CONFLICT DO NOTHING""",
            notification_id, delivery.user_id, category,
        )
        # Блокировка строки: дубль, пришедший параллельно, подождёт и увидит status = sent
        row = await db.fetchrow(
            'SELECT status FROM notify.notifications WHERE notification_id = $1 FOR UPDATE',
            notification_id,
        )
        if row['status'] in ('sent', 'skipped'):
            return f'{notification_id}: дубль, уже {row["status"]}'

        async def mark(status: str, reason: str | None = None, **extra) -> str:
            await db.execute(
                """UPDATE notify.notifications
                   SET status = $2, reason = $3, send_after = $4, payload = $5,
                       sent_at = CASE WHEN $2 = 'sent' THEN now() END
                   WHERE notification_id = $1""",
                notification_id, status, reason, extra.get('send_after'), extra.get('payload'),
            )
            return f'{notification_id}: {status}' + (f' ({reason})' if reason else '')

        if delivery.skip_reason:
            return await mark('skipped', delivery.skip_reason)

        unsubscribed = await db.fetchval(
            'SELECT 1 FROM notify.unsubscribes WHERE user_id = $1 AND category = $2',
            delivery.user_id, category,
        )
        if unsubscribed:
            return await mark('skipped', f'отписан от {category}')

        settings = await db.fetchrow(
            'SELECT * FROM notify.user_settings WHERE user_id = $1', delivery.user_id
        )
        if not released and not EVENT_TYPES[event['type']]['urgent']:
            until = quiet_until(
                datetime.now(UTC), settings['timezone'], settings['quiet_from'], settings['quiet_to']
            )
            if until:
                payload = json.dumps({**event, 'recipient_id': delivery.user_id})
                return await mark('deferred', 'тихие часы', send_after=until, payload=payload)

        user = await db.fetchrow('SELECT name, email FROM tasker.users WHERE id = $1', delivery.user_id)
        template = await db.fetchrow('SELECT * FROM notify.templates WHERE name = $1', event['type'])
        context = {**delivery.context, 'user': dict(user)}

        message = EmailMessage()
        message['From'] = 'Задачник <noreply@tasker.local>'
        message['To'] = user['email']
        message['Subject'] = jinja.from_string(template['subject']).render(context)
        message['X-Notification-Id'] = notification_id
        message.set_content(jinja.from_string(template['body']).render(context))

        await smtp_limiter.wait()
        await aiosmtplib.send(message, hostname=SMTP_HOST, port=SMTP_PORT, timeout=5)
        # Если упадём между отправкой и COMMIT, письмо уйдёт ещё раз: это цена at-least-once
        return await mark('sent')


async def handle(pool: asyncpg.Pool, event: dict) -> None:
    async with pool.acquire() as db:
        deliveries = await build_deliveries(db, event)
    if 'recipient_id' in event:
        deliveries = [d for d in deliveries if d.user_id == event['recipient_id']]
    for delivery in deliveries:
        result = await deliver(pool, event, delivery, event.get('released', False))
        log.info(result)


async def main() -> None:
    pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=PREFETCH)
    connection = await aio_pika.connect_robust(RABBIT_URL)
    channel = await connection.channel(publisher_confirms=True)
    await declare_topology(channel)
    # Не больше PREFETCH неподтверждённых сообщений на воркер: это и есть регулятор нагрузки
    await channel.set_qos(prefetch_count=PREFETCH)
    queue = await channel.get_queue(QUEUE)

    async def send_to(queue_name: str, message: aio_pika.abc.AbstractIncomingMessage, headers: dict):
        await channel.default_exchange.publish(
            aio_pika.Message(
                body=message.body,
                content_type=message.content_type,
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                message_id=message.message_id,
                headers={**(message.headers or {}), **headers},
            ),
            routing_key=queue_name,
        )

    async def on_message(message: aio_pika.abc.AbstractIncomingMessage) -> None:
        attempt = int((message.headers or {}).get('x-attempt', 0)) + 1
        try:
            try:
                event = json.loads(message.body)
                if event.get('type') not in EVENT_TYPES:
                    raise BadMessage(f"неизвестный тип {event.get('type')}")
            except ValueError as exc:
                raise BadMessage(f'не JSON: {exc}') from exc
            await handle(pool, event)
        except BadMessage as exc:
            log.warning('%s → DLQ сразу: %s', message.message_id, exc)
            await send_to(DLQ, message, {'x-error': str(exc), 'x-attempt': attempt})
        except Exception as exc:
            if attempt >= MAX_ATTEMPTS:
                log.warning('%s попытка %d/%d → DLQ: %r', message.message_id, attempt, MAX_ATTEMPTS, exc)
                await send_to(DLQ, message, {'x-error': repr(exc), 'x-attempt': attempt})
            else:
                log.warning('%s попытка %d/%d → %s: %r',
                            message.message_id, attempt, MAX_ATTEMPTS, retry_queue(attempt), exc)
                await send_to(retry_queue(attempt), message, {'x-attempt': attempt})
        # Подтверждаем, только когда письмо отправлено или сообщение переложено с подтверждением.
        # Если упал сам send_to, ack не будет и брокер вернёт сообщение после разрыва канала
        await message.ack()

    await queue.consume(on_message)
    log.info('Воркер слушает %s, prefetch=%d', QUEUE, PREFETCH)
    try:
        await asyncio.Future()
    finally:
        await connection.close()
        await pool.close()


if __name__ == '__main__':
    asyncio.run(main())
