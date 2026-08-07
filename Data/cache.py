import json
import os
import time
from typing import Any, Optional

CACHE_FILE = "data/cache_store.json"


def _load_cache() -> dict:
    """Read the entire cache file from disk into a Python dict."""
    if not os.path.exists(CACHE_FILE):
        return {}
    with open(CACHE_FILE, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}


def _save_cache(cache: dict) -> None:
    """Write the entire cache dict back to disk as JSON."""
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2)


def get_cached(key: str, ttl_hours: int = 24) -> Optional[Any]:
    """
    Look up `key` in the cache.
    Returns the cached value if it exists AND is still within ttl_hours.
    Returns None if missing or expired.
    """
    cache = _load_cache()
    entry = cache.get(key)

    if entry is None:
        return None

    age_seconds = time.time() - entry["timestamp"]
    age_hours = age_seconds / 3600

    if age_hours > ttl_hours:
        return None  # stale, treat as a cache miss

    return entry["value"]


def set_cached(key: str, value: Any) -> None:
    """Save `value` under `key`, stamped with the current time."""
    cache = _load_cache()
    cache[key] = {
        "value": value,
        "timestamp": time.time()
    }
    _save_cache(cache)