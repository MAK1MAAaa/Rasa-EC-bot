from __future__ import annotations

import json
import logging
from typing import Any

try:
    from redis import asyncio as redis_asyncio
except Exception:  # pragma: no cover
    redis_asyncio = None


logger = logging.getLogger(__name__)


class RedisCache:
    def __init__(self, redis_url: str, default_ttl_sec: int = 180, key_prefix: str = "rasa_ec_bot"):
        self._redis_url = (redis_url or "").strip()
        self._default_ttl_sec = max(1, int(default_ttl_sec))
        self._key_prefix = key_prefix.strip(": ")
        self._client = None
        self._enabled = bool(self._redis_url) and redis_asyncio is not None

    @property
    def enabled(self) -> bool:
        return self._enabled and self._client is not None

    def _full_key(self, key: str) -> str:
        base = (key or "").strip()
        if not self._key_prefix:
            return base
        return f"{self._key_prefix}:{base}"

    async def connect(self) -> None:
        if not self._enabled:
            if self._redis_url and redis_asyncio is None:
                logger.warning("REDIS_URL is set but redis.asyncio is unavailable. Redis cache disabled.")
            return

        try:
            self._client = redis_asyncio.from_url(  # type: ignore[union-attr]
                self._redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
            await self._client.ping()
            logger.info("Redis cache connected.")
        except Exception as exc:
            logger.warning("Redis cache disabled due to connection error: %s", exc)
            self._enabled = False
            self._client = None

    async def close(self) -> None:
        if self._client is None:
            return
        try:
            await self._client.close()
        except Exception:
            pass
        finally:
            self._client = None

    async def get_json(self, key: str) -> Any | None:
        if not self.enabled:
            return None
        try:
            raw = await self._client.get(self._full_key(key))
            if not raw:
                return None
            return json.loads(raw)
        except Exception:
            return None

    async def set_json(self, key: str, value: Any, ttl_sec: int | None = None) -> None:
        if not self.enabled:
            return
        ttl = ttl_sec if isinstance(ttl_sec, int) and ttl_sec > 0 else self._default_ttl_sec
        try:
            payload = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
            await self._client.set(self._full_key(key), payload, ex=ttl)
        except Exception:
            return

    async def delete_keys(self, *keys: str) -> None:
        if not self.enabled:
            return
        full_keys = [self._full_key(key) for key in keys if key]
        if not full_keys:
            return
        try:
            await self._client.delete(*full_keys)
        except Exception:
            return

    async def delete_prefix(self, prefix: str) -> None:
        if not self.enabled:
            return
        normalized_prefix = (prefix or "").strip()
        if not normalized_prefix:
            return
        pattern = f"{self._full_key(normalized_prefix)}*"

        try:
            cursor = 0
            while True:
                cursor, matched_keys = await self._client.scan(cursor=cursor, match=pattern, count=200)
                if matched_keys:
                    await self._client.delete(*matched_keys)
                if cursor == 0:
                    break
        except Exception:
            return

    async def acquire_lock(self, key: str, *, token: str, ttl_sec: int) -> bool:
        if not self.enabled:
            return False
        try:
            return bool(
                await self._client.set(
                    self._full_key(key),
                    token,
                    ex=max(1, int(ttl_sec)),
                    nx=True,
                )
            )
        except Exception:
            return False

    async def release_lock(self, key: str, *, token: str) -> None:
        if not self.enabled:
            return
        full_key = self._full_key(key)
        try:
            current = await self._client.get(full_key)
            if current == token:
                await self._client.delete(full_key)
        except Exception:
            return
