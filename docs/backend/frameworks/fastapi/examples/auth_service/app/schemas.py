from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class Credentials(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserOut(BaseModel):
    id: int
    email: EmailStr
    roles: list[str]


class MeOut(UserOut):
    permissions: list[str]


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = 'bearer'


class RefreshIn(BaseModel):
    refresh_token: str


class PasswordChangeIn(BaseModel):
    old_password: str
    new_password: str = Field(min_length=8, max_length=128)


class LoginRecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_agent: str
    ip: str | None
    success: bool
    created_at: datetime


class SessionOut(BaseModel):
    sid: str
    user_agent: str
    ip: str
    created_at: datetime
    current: bool
