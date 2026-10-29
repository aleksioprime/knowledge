from datetime import date, datetime

from sqlalchemy import ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class User(Base):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    hashed_password: Mapped[str]

    tasks: Mapped[list['Task']] = relationship(back_populates='owner')


class Task(Base):
    __tablename__ = 'tasks'

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    done: Mapped[bool] = mapped_column(default=False)
    priority: Mapped[int] = mapped_column(default=1, server_default='1')
    due_date: Mapped[date | None]
    reminder_sent: Mapped[bool] = mapped_column(default=False, server_default='false')
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    owner_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)

    owner: Mapped[User] = relationship(back_populates='tasks')
