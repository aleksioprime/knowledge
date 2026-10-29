from datetime import datetime

from sqlalchemy import BigInteger, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from src.database.db import Base


class Link(Base):
    __tablename__ = 'links'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    code: Mapped[str] = mapped_column(String(10), unique=True)
    url: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
