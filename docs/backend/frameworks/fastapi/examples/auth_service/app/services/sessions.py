import time
from enum import Enum

from redis.asyncio import Redis

# Сравнить jti и заменить его должно одной операцией: иначе два параллельных
# запроса с одним refresh-токеном оба увидят «совпало» и оба получат новую пару.
ROTATE_SCRIPT = """
local current = redis.call('HGET', KEYS[1], 'refresh_jti')
if not current then return -1 end
if current ~= ARGV[1] then return 0 end
redis.call('HSET', KEYS[1], 'refresh_jti', ARGV[2], 'access_jti', ARGV[3], 'access_exp', ARGV[4])
redis.call('EXPIRE', KEYS[1], ARGV[5])
return 1
"""


class Rotation(Enum):
    OK = 1
    REUSED = 0
    UNKNOWN = -1


class SessionStore:
    """Refresh-сессии, чёрный список access-токенов и версии токенов в Redis.

    session:{sid}          hash  user_id, refresh_jti, access_jti, access_exp, user_agent, ip, created_at
    user:{id}:sessions     set   sid всех сессий пользователя
    user:{id}:token_ver    int   растёт при «выйти везде» и смене пароля
    denylist:{jti}         "1"   отозванный access-токен, живёт до его exp
    """

    def __init__(self, redis: Redis, refresh_ttl: int):
        self.redis = redis
        self.refresh_ttl = refresh_ttl
        self._rotate = redis.register_script(ROTATE_SCRIPT)

    async def create(
        self, user_id: int, sid: str, refresh_jti: str, access_jti: str, access_exp: int,
        user_agent: str, ip: str,
    ) -> None:
        key = f'session:{sid}'
        sessions_key = f'user:{user_id}:sessions'
        async with self.redis.pipeline(transaction=True) as pipe:
            pipe.hset(key, mapping={
                'user_id': user_id, 'refresh_jti': refresh_jti,
                'access_jti': access_jti, 'access_exp': access_exp,
                'user_agent': user_agent, 'ip': ip, 'created_at': int(time.time()),
            })
            pipe.expire(key, self.refresh_ttl)
            pipe.sadd(sessions_key, sid)
            pipe.expire(sessions_key, self.refresh_ttl)
            await pipe.execute()

    async def rotate(
        self, sid: str, old_jti: str, new_refresh_jti: str, access_jti: str, access_exp: int,
    ) -> Rotation:
        result = await self._rotate(
            keys=[f'session:{sid}'],
            args=[old_jti, new_refresh_jti, access_jti, access_exp, self.refresh_ttl],
        )
        return Rotation(int(result))

    async def revoke(self, sid: str) -> None:
        session = await self.redis.hgetall(f'session:{sid}')
        if not session:
            return
        await self.deny_access(session['access_jti'], int(session['access_exp']))
        await self.redis.delete(f'session:{sid}')
        await self.redis.srem(f'user:{session["user_id"]}:sessions', sid)

    async def revoke_all(self, user_id: int) -> None:
        for sid in await self.redis.smembers(f'user:{user_id}:sessions'):
            await self.revoke(sid)
        await self.redis.delete(f'user:{user_id}:sessions')
        await self.redis.incr(f'user:{user_id}:token_ver')

    async def list_sessions(self, user_id: int) -> list[dict]:
        sessions = []
        for sid in await self.redis.smembers(f'user:{user_id}:sessions'):
            session = await self.redis.hgetall(f'session:{sid}')
            if session:
                sessions.append({'sid': sid, **session})
            else:
                await self.redis.srem(f'user:{user_id}:sessions', sid)  # истекла по TTL
        return sorted(sessions, key=lambda s: int(s['created_at']))

    async def deny_access(self, jti: str, exp: int) -> None:
        ttl = exp - int(time.time())
        if ttl > 0:
            await self.redis.set(f'denylist:{jti}', 1, ex=ttl)

    async def is_denied(self, jti: str) -> bool:
        return await self.redis.exists(f'denylist:{jti}') == 1

    async def token_version(self, user_id: int) -> int:
        return int(await self.redis.get(f'user:{user_id}:token_ver') or 0)
