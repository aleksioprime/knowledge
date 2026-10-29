import asyncio
import logging
import random

from fastapi import FastAPI, HTTPException
from opentelemetry import trace

from app.telemetry import setup_logging, setup_tracing

USERS = {10: {'id': 10, 'name': 'Анна'}}

logger = logging.getLogger('users')
tracer = trace.get_tracer('users')

app = FastAPI()
setup_logging()
setup_tracing(app)


@app.get('/users/{user_id}')
async def get_user(user_id: int):
    span = trace.get_current_span()
    span.add_event('кэш пуст, идём в базу', {'user.id': user_id})

    with tracer.start_as_current_span('SELECT user') as db_span:
        db_span.set_attribute('db.system.name', 'postgresql')
        db_span.set_attribute('db.query.text', 'SELECT id, name FROM "user" WHERE id = $1')
        # имитация запроса в базу: обычно 80 мс, но каждый двадцатый — полсекунды
        await asyncio.sleep(0.5 if random.random() < 0.05 else 0.08)
        user = USERS.get(user_id)

    if user is None:
        logger.warning('пользователь %s не найден', user_id)
        raise HTTPException(404, 'пользователь не найден')
    logger.info('пользователь %s найден', user_id)
    return user
