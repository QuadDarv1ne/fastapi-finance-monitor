"""Tests for the Redis cache service"""

import pytest
import asyncio
from app.services.redis_cache_service import RedisCacheService


def test_redis_cache_service_import():
    """Test that RedisCacheService can be imported"""
    assert RedisCacheService is not None


if __name__ == "__main__":
    pytest.main([__file__])
