"""Redis-based presence tracking: online / AFK / offline."""
import json
import time

import redis.asyncio as aioredis

from app.config import settings

_redis: aioredis.Redis | None = None


def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis


# TTL for a tab registration: 300s handles Chrome's background tab timer throttling
TAB_TTL = 300
AFK_THRESHOLD = settings.AFK_TIMEOUT_SECONDS


async def tab_connect(user_id: str, tab_id: str) -> None:
    r = get_redis()
    now = time.time()
    await r.hset(f"user_tabs:{user_id}", tab_id, now)
    await r.set(f"tab_active:{user_id}:{tab_id}", "1", ex=TAB_TTL)
    await r.set(f"tab_activity_time:{user_id}:{tab_id}", str(now), ex=TAB_TTL)
    status = await _update_presence(r, user_id)
    # Always broadcast on connect so users who loaded before this connection see the update
    await r.publish("presence_updates", json.dumps({"user_id": user_id, "status": status}))


async def tab_disconnect(user_id: str, tab_id: str) -> None:
    r = get_redis()
    await r.hdel(f"user_tabs:{user_id}", tab_id)
    await r.delete(f"tab_active:{user_id}:{tab_id}")
    await r.delete(f"tab_activity_time:{user_id}:{tab_id}")
    await _update_presence(r, user_id)


async def tab_heartbeat(user_id: str, tab_id: str, active: bool) -> str:
    r = get_redis()
    now = time.time()
    await r.hset(f"user_tabs:{user_id}", tab_id, now)
    if active:
        await r.set(f"tab_active:{user_id}:{tab_id}", "1", ex=TAB_TTL)
        await r.set(f"tab_activity_time:{user_id}:{tab_id}", str(now), ex=TAB_TTL)
    else:
        # Refresh TTL so tab is still "registered" but not active
        await r.set(f"tab_active:{user_id}:{tab_id}", "0", ex=TAB_TTL)
    return await _update_presence(r, user_id)


async def get_presence(user_id: str) -> str:
    r = get_redis()
    val = await r.get(f"presence:{user_id}")
    return val or "offline"


async def get_presence_many(user_ids: list[str]) -> dict[str, str]:
    if not user_ids:
        return {}
    r = get_redis()
    pipe = r.pipeline()
    for uid in user_ids:
        pipe.get(f"presence:{uid}")
    results = await pipe.execute()
    return {uid: (val or "offline") for uid, val in zip(user_ids, results, strict=False)}


async def _update_presence(r: aioredis.Redis, user_id: str) -> str:
    tabs = await r.hgetall(f"user_tabs:{user_id}")

    if not tabs:
        status = "offline"
    else:
        now = time.time()
        # Check if any tab is active (has recent activity)
        any_active = False
        live_tabs = 0
        for tab_id in tabs:
            active_val = await r.get(f"tab_active:{user_id}:{tab_id}")
            if active_val is None:
                # Key expired — tab is gone, prune stale entry
                await r.hdel(f"user_tabs:{user_id}", tab_id)
                continue
            live_tabs += 1
            if active_val == "1":
                activity_time_val = await r.get(f"tab_activity_time:{user_id}:{tab_id}")
                if activity_time_val:
                    last_activity = float(activity_time_val)
                    if now - last_activity < AFK_THRESHOLD:
                        any_active = True
                        break
                else:
                    # Tab connected but no explicit activity yet — treat as active
                    any_active = True
                    break

        if live_tabs == 0:
            status = "offline"
        else:
            status = "online" if any_active else "afk"

    old = await r.get(f"presence:{user_id}")
    await r.set(f"presence:{user_id}", status, ex=TAB_TTL * 2)

    if old != status:
        # Publish presence change for subscribers
        await r.publish("presence_updates", json.dumps({"user_id": user_id, "status": status}))

    return status
