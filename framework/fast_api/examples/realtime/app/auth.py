import time

import jwt


def create_token(user_id: str, secret: str, ttl: int = 3600) -> str:
    now = int(time.time())
    return jwt.encode({'sub': user_id, 'iat': now, 'exp': now + ttl}, secret, algorithm='HS256')


def user_from_token(token: str | None, secret: str) -> str | None:
    if not token:
        return None
    try:
        payload = jwt.decode(token, secret, algorithms=['HS256'])
    except jwt.InvalidTokenError:
        return None
    return payload.get('sub')
