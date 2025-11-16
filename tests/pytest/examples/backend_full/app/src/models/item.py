"""Модели элемента, группы и тега"""
import uuid

from sqlalchemy import  String, Boolean, ForeignKey, relationship
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, UUIDMixin, TimestampMixin


class Group(UUIDMixin, TimestampMixin, Base):
    """
    Модель группы
    """
    __tablename__ = 'groups'

    name: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255))

    items: Mapped[list["Item"]] = relationship(back_populates="group", lazy="selectin")


class Item(UUIDMixin, TimestampMixin, Base):
    """
    Модель элемента
    """
    __tablename__ = "items"

    name: Mapped[str] = mapped_column(String, index=True)
    price: Mapped[float] = mapped_column()

    tags: Mapped[list["Tag"]] = mapped_column(
        secondary="item_tags",
        back_populates="items"
    )

    group_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("groups.id", ondelete="SET NULL"),
        nullable=True,
    )
    group: Mapped["Group | None"] = relationship(back_populates="items", lazy="selectin")


class Tag(UUIDMixin, TimestampMixin, Base):
    """
    Модель тега
    """
    __tablename__ = "tags"

    name: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)

    items: Mapped[list[Item]] = mapped_column(
        secondary="item_tags",
        back_populates="tags"
    )