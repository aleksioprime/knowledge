from datetime import datetime

from pydantic import BaseModel, HttpUrl


class LinkCreate(BaseModel):
    url: HttpUrl


class LinkRead(BaseModel):
    code: str
    short_url: str


class LinkStats(BaseModel):
    code: str
    url: str
    clicks: int
    created_at: datetime
