"""
Simple in-memory TTL cache for API responses.

Thread-safe, bounded to MAX_ENTRIES to prevent unbounded growth.
"""
from __future__ import annotations

import functools
import threading
import time
from typing import Any, Callable

MAX_ENTRIES = 500

_lock = threading.Lock()
_cache: dict[str, tuple[float, Any]] = {}


def ttl_cache(seconds: int) -> Callable:
    """Decorator that caches function return values with a TTL.

    Cache key is built from function name + all positional/keyword args.
    Skips caching if the function raises an exception.
    """
    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            # Build key: skip `self` for method calls
            key_args = args[1:] if args and hasattr(args[0], fn.__name__) else args
            key = f"{fn.__qualname__}:{key_args}:{kwargs}"

            now = time.monotonic()
            with _lock:
                if key in _cache:
                    expires, value = _cache[key]
                    if now < expires:
                        return value
                    del _cache[key]

            result = fn(*args, **kwargs)

            with _lock:
                # Evict oldest entries if at capacity
                if len(_cache) >= MAX_ENTRIES:
                    oldest_key = min(_cache, key=lambda k: _cache[k][0])
                    del _cache[oldest_key]
                _cache[key] = (now + seconds, result)

            return result
        return wrapper
    return decorator


def clear_cache() -> int:
    """Clear all cached entries. Returns the number of entries cleared."""
    with _lock:
        count = len(_cache)
        _cache.clear()
        return count
