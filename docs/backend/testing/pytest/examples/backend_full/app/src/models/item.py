"""
Модели для управления элементами, группами и тегами.
Демонстрирует различные типы связей в SQLAlchemy: one-to-many и many-to-many.
"""
import uuid

from sqlalchemy import String, ForeignKey, Table, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, UUIDMixin, TimestampMixin


# Таблица-связка для связи many-to-many между Item и Tag
item_tags = Table(
    'item_tags',
    Base.metadata,
    Column('item_id', ForeignKey('items.id', ondelete='CASCADE'), primary_key=True),
    Column('tag_id', ForeignKey('tags.id', ondelete='CASCADE'), primary_key=True),
)


class Group(UUIDMixin, TimestampMixin, Base):
    """
    Модель группы элементов.
    Группа может содержать множество элементов (one-to-many).
    """
    __tablename__ = 'groups'

    name: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255))

    # Связь с элементами: одна группа - много элементов
    # lazy="selectin" - загружает связанные объекты автоматически
    items: Mapped[list["Item"]] = relationship(back_populates="group", lazy="selectin")


class Item(UUIDMixin, TimestampMixin, Base):
    """
    Модель элемента (товара или продукта).
    Элемент может принадлежать группе и иметь множество тегов.
    """
    __tablename__ = "items"

    name: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    price: Mapped[float] = mapped_column(nullable=False)

    # Many-to-many связь с тегами через промежуточную таблицу item_tags
    tags: Mapped[list["Tag"]] = relationship(
        secondary=item_tags,
        back_populates="items",
        lazy="selectin"
    )

    # Many-to-one связь с группой (внешний ключ)
    group_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("groups.id", ondelete="SET NULL"),
        nullable=True,
    )
    group: Mapped["Group | None"] = relationship(back_populates="items", lazy="selectin")


class Tag(UUIDMixin, TimestampMixin, Base):
    """
    Модель тега для категоризации элементов.
    Тег может быть присвоен множеству элементов (many-to-many).
    """
    __tablename__ = "tags"

    name: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)

    # Many-to-many связь с элементами
    items: Mapped[list[Item]] = relationship(
        secondary=item_tags,
        back_populates="tags",
        lazy="selectin"
    )