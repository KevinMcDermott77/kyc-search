"""
Token-bucket rate limiter for Companies House API (600 req / 5 min).
Implemented as a Redis Lua script for atomicity.
"""

import asyncio

import redis.asyncio as aioredis

from app.config import settings

# 600 requests per 5-minute window (300 seconds)
CH_CAPACITY = 600
CH_REFILL_RATE = 600 / 300  # tokens per second
CH_WINDOW = 300

# Lua script: token-bucket (atomic)
_LUA_SCRIPT = """
local key = KEYS[1]
local capacity = tonumber(ARGV[1])
local rate = tonumber(ARGV[2])  -- tokens per second
local now = tonumber(ARGV[3])   -- unix timestamp (float)
local requested = tonumber(ARGV[4])

local bucket = redis.call('HMGET', key, 'tokens', 'ts')
local tokens = tonumber(bucket[1]) or capacity
local ts = tonumber(bucket[2]) or now

-- refill
local delta = math.max(0, now - ts)
tokens = math.min(capacity, tokens + delta * rate)

if tokens < requested then
    return 0
end

tokens = tokens - requested
redis.call('HMSET', key, 'tokens', tokens, 'ts', now)
redis.call('EXPIRE', key, 600)
return 1
"""

_redis: aioredis.Redis | None = None
_script: object | None = None


async def _get_redis() -> aioredis.Redis:
    global _redis, _script
    if _redis is None:
        _redis = aioredis.from_url(settings.redis_url, decode_responses=True)
        _script = _redis.register_script(_LUA_SCRIPT)
    return _redis


async def acquire_ch_token() -> None:
    """Block until a Companies House API token is available."""
    import time
    r = await _get_redis()
    while True:
        now = time.time()
        allowed = await _script(  # type: ignore[misc]
            keys=["ch_rate_bucket"],
            args=[CH_CAPACITY, CH_REFILL_RATE, now, 1],
        )
        if allowed:
            return
        await asyncio.sleep(0.5)
