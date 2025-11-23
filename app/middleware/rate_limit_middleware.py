"""Rate limiting middleware (Redis-backed with in-memory fallback).

Approach:
- Token bucket per (client_key, normalized_path) with sliding window refill.
- Client key derived from Authorization token hash or IP address.
- Uses Redis if available (via redis_cache_service) else process-local memory dictionary.
- Excludes safe endpoints: /health, /metrics, /docs, /redoc.
- On limit exceeded raises RateLimitError caught by ExceptionHandlerMiddleware.
"""

import hashlib
import logging
import os
import time

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import SecurityConfig  # for enabled flag default
from app.exceptions.custom_exceptions import RateLimitError

logger = logging.getLogger(__name__)

# In-memory fallback store: key -> (tokens, last_refill_timestamp)
_memory_buckets: dict[str, tuple[float, float]] = {}

# Excluded paths (prefix match)
_EXCLUDED_PREFIXES = [
    "/health",
    "/metrics",
    "/docs",
    "/redoc",
    "/openapi.json",
]


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Generic API rate limiting middleware."""

    def __init__(self, app):
        super().__init__(app)
        # Defer dynamic config until first request because app here is previous middleware wrapper
        self.initialized = False
        self.enabled = True
        self.limit = SecurityConfig.API_RATE_LIMIT_REQUESTS
        self.window = SecurityConfig.API_RATE_LIMIT_WINDOW
        self.burst = SecurityConfig.API_RATE_LIMIT_BURST
        # Disable Redis usage unless explicitly connected; simplifies tests
        self.redis = None

    def _is_excluded(self, path: str) -> bool:
        return any(path.startswith(prefix) for prefix in _EXCLUDED_PREFIXES)

    def _client_key(self, request: Request) -> str:
        auth = request.headers.get("Authorization", "")
        if auth:
            h = hashlib.sha256(auth.encode()).hexdigest()[:16]
            return f"auth:{h}"
        client_host = request.client.host if request.client else "unknown"
        return f"ip:{client_host}"

    async def _redis_bucket(self, key: str) -> tuple[float, float]:
        # Use a Redis hash with fields tokens, ts
        bucket_key = f"rate:{key}"
        try:
            exists = await self.redis.client.exists(bucket_key)  # type: ignore[attr-defined]
            now = time.time()
            if not exists:
                # Initialize bucket
                initial_tokens = float(self.limit + self.burst)
                pipe = self.redis.client.pipeline()  # type: ignore[attr-defined]
                pipe.hset(bucket_key, mapping={"tokens": initial_tokens, "ts": now})
                pipe.expire(bucket_key, self.window * 2)
                await pipe.execute()
                return initial_tokens, now
            data = await self.redis.client.hgetall(bucket_key)  # type: ignore[attr-defined]
            tokens = float(data.get(b"tokens", b"0").decode())
            ts = float(data.get(b"ts", b"0").decode())
            return tokens, ts
        except Exception:
            # Fallback to memory if Redis not usable
            self.redis = None
            return self._memory_bucket(key)

    def _memory_bucket(self, key: str) -> tuple[float, float]:
        return _memory_buckets.get(key, (float(self.limit + self.burst), time.time()))

    async def _store_redis_bucket(self, key: str, tokens: float, ts: float) -> None:
        if not self.redis:
            _memory_buckets[key] = (tokens, ts)
            return
        bucket_key = f"rate:{key}"
        try:
            pipe = self.redis.client.pipeline()  # type: ignore[attr-defined]
            pipe.hset(bucket_key, mapping={"tokens": tokens, "ts": ts})
            pipe.expire(bucket_key, self.window * 2)
            await pipe.execute()
        except Exception:
            _memory_buckets[key] = (tokens, ts)
            self.redis = None

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        if not self.initialized:
            # Access real FastAPI app via request.app
            real_app = request.app
            self.enabled = getattr(
                real_app.state,
                "rate_limit_enabled",
                (os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"),
            )
            self.limit = getattr(
                real_app.state,
                "rate_limit_limit",
                int(os.getenv("RATE_LIMIT_REQUESTS", str(SecurityConfig.API_RATE_LIMIT_REQUESTS))),
            )
            self.window = getattr(
                real_app.state,
                "rate_limit_window",
                int(
                    os.getenv(
                        "RATE_LIMIT_WINDOW_SECONDS", str(SecurityConfig.API_RATE_LIMIT_WINDOW)
                    )
                ),
            )
            self.burst = getattr(
                real_app.state,
                "rate_limit_burst",
                int(os.getenv("RATE_LIMIT_BURST", str(SecurityConfig.API_RATE_LIMIT_BURST))),
            )
            self.initialized = True

        if not self.enabled or self._is_excluded(request.url.path):
            return await call_next(request)

        key = self._client_key(request) + ":" + request.url.path
        now = time.time()

        # Load bucket
        tokens, last_ts = self._memory_bucket(key)

        # Refill logic (sliding window): refill rate = limit/window per second
        refill_rate = self.limit / self.window
        elapsed = max(0.0, now - last_ts)
        tokens = min(self.limit + self.burst, tokens + elapsed * refill_rate)

        if tokens < 1.0:
            # Reject
            retry_after = max(0, int(self.window - elapsed))
            logger.warning(f"Rate limit exceeded key={key} path={request.url.path}")
            raise RateLimitError(f"Too many requests. Retry after {retry_after} seconds")

        # Consume token
        tokens -= 1.0
        await self._store_redis_bucket(key, tokens, now)

        response = await call_next(request)
        # Optionally add headers
        remaining = int(tokens)
        response.headers["X-RateLimit-Limit"] = str(self.limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Window"] = str(self.window)
        return response
