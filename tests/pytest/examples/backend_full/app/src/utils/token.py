import time
from jwt import ExpiredSignatureError, InvalidTokenError, decode

from src.core.config import settings


class JWTHelper:
    @staticmethod
    def decode(token: str) -> dict | None:
        try:
            decoded_token = decode(
                token,
                settings.jwt.secret_key,
                algorithms=[settings.jwt.algorithm],
            )
            return decoded_token if decoded_token['exp'] >= time.time() else None
        except (ExpiredSignatureError, InvalidTokenError):
            return None