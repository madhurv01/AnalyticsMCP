import time

import redis
from fastapi import HTTPException, Request, status

from app.config import settings

_r = redis.Redis.from_url(settings.redis_url, decode_responses=True)

# route class -> (limit, window seconds)
LIMITS = {
    "auth": (10, 300),
    "upload": (20, 3600),
    "analyze": (30, 3600),
    "read": (240, 60),
    "mcp": (120, 60),
}


def _check(bucket: str, ident: str, route_class: str) -> None:
    limit, window = LIMITS[route_class]
    slot = int(time.time()) // window
    key = f"rl:{bucket}:{route_class}:{slot}"
    try:
        count = _r.incr(key)
        if count == 1:
            _r.expire(key, window)
    except redis.RedisError:
        return  # fail open — limiter must never take the app down
    if count > limit:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            detail="rate limit exceeded",
            headers={"Retry-After": str(window)},
        )


def limit(route_class: str):
    def dep(request: Request) -> None:
        user = request.cookies.get(settings.session_cookie)
        ident = user or (request.client.host if request.client else "anon")
        _check(ident[:64], ident, route_class)

    return dep
