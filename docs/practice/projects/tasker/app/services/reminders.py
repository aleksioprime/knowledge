from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.email import send_email
from app.models import Task


async def find_tasks_to_remind(session: AsyncSession, today: date) -> list[int]:
    query = select(Task.id).where(
        Task.due_date == today + timedelta(days=1),
        Task.done.is_(False),
        Task.reminder_sent.is_(False),
    )
    return list(await session.scalars(query))


async def send_reminder(session: AsyncSession, task_id: int) -> bool:
    task = await session.scalar(select(Task).options(selectinload(Task.owner)).where(Task.id == task_id))
    # Задачу могли выполнить или уже напомнить о ней: повторный запуск ничего не сломает
    if task is None or task.done or task.reminder_sent:
        return False
    send_email(task.owner.email, 'Срок задачи — завтра', task.title)
    task.reminder_sent = True
    await session.commit()
    return True
