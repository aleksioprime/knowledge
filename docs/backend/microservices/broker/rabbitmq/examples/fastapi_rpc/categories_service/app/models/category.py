from sqlalchemy import Column, Integer, String

from app.core.database import Base


class Category(Base):
    """Модель категории"""
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)