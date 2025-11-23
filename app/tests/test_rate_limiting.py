import time

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.middleware.exception_handler_middleware import ExceptionHandlerMiddleware
from app.middleware.rate_limit_middleware import RateLimitMiddleware


def create_app(limit: int = 5, window: int = 1):
    # Override env vars for test
    import os

    os.environ["RATE_LIMIT_ENABLED"] = "true"
    os.environ["RATE_LIMIT_REQUESTS"] = str(limit)
    os.environ["RATE_LIMIT_WINDOW_SECONDS"] = str(window)
    os.environ["RATE_LIMIT_BURST"] = "0"

    app = FastAPI()
    # Set app.state overrides before middleware init
    app.state.rate_limit_enabled = True
    app.state.rate_limit_limit = limit
    app.state.rate_limit_window = window
    app.state.rate_limit_burst = 0
    # Reset in-memory buckets between tests
    from app.middleware import rate_limit_middleware as rl_mod

    rl_mod._memory_buckets.clear()  # type: ignore[attr-defined]
    # Add rate limiter first so exception handler wraps it externally
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(ExceptionHandlerMiddleware)

    @app.get("/ping")
    def ping():
        return {"ok": True}

    return app


def test_rate_limit_basic():
    app = create_app(limit=3, window=2)
    client = TestClient(app)

    # First 3 requests succeed
    for i in range(3):
        r = client.get("/ping")
        assert r.status_code == 200, f"Expected success for request {i+1}"

    # 4th should be limited
    r4 = client.get("/ping")
    assert r4.status_code == 429
    assert r4.json()["error"] == "Rate limit exceeded"

    # Wait for window to pass
    time.sleep(2.2)

    # Should succeed again
    r5 = client.get("/ping")
    assert r5.status_code == 200


def test_rate_limit_headers_present():
    app = create_app(limit=2, window=5)
    client = TestClient(app)

    r1 = client.get("/ping")
    assert r1.status_code == 200
    assert "X-RateLimit-Limit" in r1.headers
    assert "X-RateLimit-Remaining" in r1.headers
    assert r1.headers["X-RateLimit-Limit"] == "2"

    r2 = client.get("/ping")
    assert r2.status_code == 200
    assert r2.headers["X-RateLimit-Remaining"] == "0"

    r3 = client.get("/ping")
    assert r3.status_code == 429


def test_rate_limit_excluded_paths():
    app = create_app(limit=1, window=10)
    client = TestClient(app)

    # /health should not be limited (middleware exclusion)
    @app.get("/health")
    def health():  # pragma: no cover
        return {"status": "ok"}

    # Access health multiple times
    for _ in range(3):
        rh = client.get("/health")
        assert rh.status_code == 200

    # /ping limited after first request
    r1 = client.get("/ping")
    assert r1.status_code == 200
    r2 = client.get("/ping")
    assert r2.status_code == 429
