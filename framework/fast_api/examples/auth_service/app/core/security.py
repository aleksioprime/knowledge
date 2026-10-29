from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
from pwdlib import PasswordHash

from app.core.config import settings

ALGORITHM = 'HS256'
password_hash = PasswordHash.recommended()


@dataclass
class IssuedToken:
    token: str
    jti: str
    exp: int


def _issue(claims: dict, ttl: timedelta) -> IssuedToken:
    now = datetime.now(UTC)
    jti = uuid4().hex
    exp = now + ttl
    payload = {**claims, 'jti': jti, 'iat': now, 'exp': exp}
    token = jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)
    return IssuedToken(token=token, jti=jti, exp=int(exp.timestamp()))


def create_access_token(user_id: int, sid: str, roles: list[str], version: int) -> IssuedToken:
    claims = {'sub': str(user_id), 'sid': sid, 'type': 'access', 'roles': roles, 'ver': version}
    return _issue(claims, timedelta(minutes=settings.access_ttl_minutes))


def create_refresh_token(user_id: int, sid: str) -> IssuedToken:
    claims = {'sub': str(user_id), 'sid': sid, 'type': 'refresh'}
    return _issue(claims, timedelta(days=settings.refresh_ttl_days))


def decode_token(token: str, expected_type: str) -> dict | None:
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[ALGORITHM],
            options={'require': ['exp', 'sub', 'jti', 'sid', 'type']},
        )
    except jwt.InvalidTokenError:
        return None
    # refresh-токен не должен открывать API, а access — обновлять сессию
    if payload['type'] != expected_type:
        return None
    return payload
