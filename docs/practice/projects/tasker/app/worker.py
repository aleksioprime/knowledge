import asyncio
from datetime import date

from celery import Celery
from celery.schedules import crontab
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.services import reminders

celery_app = Celery('tasker', broker=settings.celery_broker_url)
celery_app.conf.update(
    timezone='Europe/Moscow',
    task_acks_late=True,
    beat_schedule={
        'remind-about-due-tasks': {
            'task': 'app.worker.remind_about_due_tasks',
            'schedule': crontab(hour=9, minute=0),
        },
    },
)

# Каждая задача Celery запускает свой цикл событий через asyncio.run,
# поэтому пул соединений между ними не переиспользуем
engine = create_async_engine(settings.database_url, poolclass=NullPool)
Session = async_sessionmaker(engine, expire_on_commit=False)


async def _find_tasks_to_remind() -> list[int]:
    async with Session() as session:
        return await reminders.find_tasks_to_remind(session, date.today())


async def _send_reminder(task_id: int) -> bool:
    async with Session() as session:
        return await reminders.send_reminder(session, task_id)


@celery_app.task
def remind_about_due_tasks() -> int:
    task_ids = asyncio.run(_find_tasks_to_remind())
    for task_id in task_ids:
        send_reminder.delay(task_id)
    return len(task_ids)


@celery_app.task(autoretry_for=(ConnectionError,), retry_backoff=True, max_retries=5)
def send_reminder(task_id: int) -> bool:
    return asyncio.run(_send_reminder(task_id))
