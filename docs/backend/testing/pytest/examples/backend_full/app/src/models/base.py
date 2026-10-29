"""
Базовые модели и миксины для SQLAlchemy.
Содержит общие поля и функциональность для всех моделей БД.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from src.db.postgres import Base
from src.utils.time import utc_now


class UUIDMixin:
    """
    Миксин для добавления UUID в качестве первичного ключа.
    Автоматически генерирует уникальный идентификатор для каждой записи.
    """
    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        unique=True,
        nullable=False
    )


class TimestampMixin:
    """
    Миксин для добавления временных меток создания и обновления.
    Автоматически устанавливает время создания и обновления записи.
    """
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,  # Значение по умолчанию в Python
        server_default=func.now(),  # Значение по умолчанию в БД
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,  # Обновляется при изменении записи
        server_default=func.now(),
        server_onupdate=func.now(),  # Автообновление на стороне БД
        nullable=False,
    )


__all__ = ["Base", "UUIDMixin", "TimestampMixin"]