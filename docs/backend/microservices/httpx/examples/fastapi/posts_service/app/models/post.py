from sqlalchemy import Column, Integer, String

from app.core.database import Base


class Post(Base):
    """Модель поста"""
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True)
    title = Column(String, index=True)
    content = Column(String)
    category_id = Column(Integer)