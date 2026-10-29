"""Планировщик: еженедельный дайджест и возврат отложенных уведомлений.

    python scheduler.py digest [--period 2026-W44] [--force]
    python scheduler.py release [--all]
"""

import argparse
import asyncio
import json
from datetime import date

import aio_pika
import asyncpg

from common import DATABASE_URL, EXCHANGE, RABBIT_URL, routing_key

JOB = 'weekly-digest'
BATCH_SIZE = 100


def current_period() -> str:
    year, week, _ = date.today().isocalendar()
    return f'{year}-W{week:02d}'


async def publish(exchange: aio_pika.abc.AbstractExchange, event: dict) -> None:
    await exchange.publish(
        aio_pika.Message(
            body=json.dumps(event, ensure_ascii=False).encode(),
            content_type='application/json',
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            message_id=event['event_id'],
        ),
        routing_key=routing_key(event['type']),
        mandatory=True,
    )


async def digest(db: asyncpg.Connection, exchange, period: str, force: bool) -> None:
    await db.execute(
        """INSERT INTO notify.scheduler_runs (job, period, status) VALUES ($1, $2, 'started')
           ON CONFLICT DO NOTHING""",
        JOB, period,
    )
    status = await db.fetchval(
        'SELECT status FROM notify.scheduler_runs WHERE job = $1 AND period = $2', JOB, period
    )
    if status == 'done' and not force:
        print(f'{JOB} {period}: уже выполнен, пропускаю')
        return
    # status = started: прошлый запуск упал на середине. Запускаем заново —
    # ключ digest:<период>:<пользователь> не даст отправить письмо второй раз

    last_id, sent = 0, 0
    while True:
        # Пачка пользователей и их задачи — двумя запросами, а не запросом на каждого
        users = await db.fetch(
            'SELECT id FROM tasker.users WHERE id > $1 ORDER BY id LIMIT $2', last_id, BATCH_SIZE
        )
        if not users:
            break
        ids = [u['id'] for u in users]
        tasks = await db.fetch(
            """SELECT assignee_id, title, due_date < CURRENT_DATE AS overdue
               FROM tasker.tasks WHERE status = 'open' AND assignee_id = ANY($1) ORDER BY id""",
            ids,
        )
        for user_id in ids:
            user_tasks = [
                {'title': t['title'], 'overdue': bool(t['overdue'])}
                for t in tasks if t['assignee_id'] == user_id
            ]
            await publish(exchange, {
                'event_id': f'digest:{period}',
                'type': 'digest.weekly',
                'data': {'user_id': user_id, 'period': period, 'tasks': user_tasks},
                'recipient_id': user_id,
            })
            sent += 1
        print(f'{JOB} {period}: пачка из {len(ids)} пользователей опубликована')
        last_id = ids[-1]

    await db.execute(
        """UPDATE notify.scheduler_runs SET status = 'done', finished_at = now()
           WHERE job = $1 AND period = $2""",
        JOB, period,
    )
    print(f'{JOB} {period}: готово, событий {sent}')


async def release(db: asyncpg.Connection, exchange, release_all: bool) -> None:
    rows = await db.fetch(
        """SELECT notification_id, payload FROM notify.notifications
           WHERE status = 'deferred' AND ($1 OR send_after <= now())""",
        release_all,
    )
    for row in rows:
        event = json.loads(row['payload'])
        await publish(exchange, {**event, 'released': True})
        # Условие на статус: воркер мог успеть отправить письмо раньше, чем мы сюда дошли
        await db.execute(
            """UPDATE notify.notifications SET status = 'queued'
               WHERE notification_id = $1 AND status = 'deferred'""",
            row['notification_id'],
        )
        print(f"release: {row['notification_id']} снова в очереди")
    print(f'release: возвращено {len(rows)}')


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['digest', 'release'])
    parser.add_argument('--period', default=current_period())
    parser.add_argument('--force', action='store_true', help='запустить, даже если период выполнен')
    parser.add_argument('--all', action='store_true', help='вернуть отложенные, не дожидаясь утра')
    args = parser.parse_args()

    db = await asyncpg.connect(DATABASE_URL)
    connection = await aio_pika.connect_robust(RABBIT_URL)
    channel = await connection.channel(publisher_confirms=True, on_return_raises=True)
    exchange = await channel.get_exchange(EXCHANGE)
    try:
        if args.command == 'digest':
            await digest(db, exchange, args.period, args.force)
        else:
            await release(db, exchange, args.all)
    finally:
        await connection.close()
        await db.close()


if __name__ == '__main__':
    asyncio.run(main())
