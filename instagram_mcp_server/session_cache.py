"""Session cache for Instagram to avoid repeated API calls and rate limiting."""

import asyncio
import time
from typing import Optional
from pathlib import Path
import json
import logging

logger = logging.getLogger(__name__)

# Cache configuration
_SESSION_CACHE_FILE = Path.home() / ".instagram-mcp" / "session_cache.json"
_SESSION_CACHE_TTL = 300  # 5 minutes cache TTL
_RATE_LIMIT_COOLDOWN = 60  # 1 minute cooldown after rate limit

class SessionCache:
    """Cache for Instagram session validation to avoid rate limiting."""
    
    def __init__(self):
        self._cache_data: dict = {}
        self._last_rate_limit_time: float = 0
        self._load_cache()
    
    def _load_cache(self) -> None:
        """Load cache from disk."""
        try:
            if _SESSION_CACHE_FILE.exists():
                with open(_SESSION_CACHE_FILE, 'r') as f:
                    self._cache_data = json.load(f)
                logger.debug("Session cache loaded from disk")
        except Exception as e:
            logger.warning(f"Failed to load session cache: {e}")
            self._cache_data = {}
    
    def _save_cache(self) -> None:
        """Save cache to disk."""
        try:
            _SESSION_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(_SESSION_CACHE_FILE, 'w') as f:
                json.dump(self._cache_data, f)
            logger.debug("Session cache saved to disk")
        except Exception as e:
            logger.warning(f"Failed to save session cache: {e}")
    
    def get(self, key: str) -> Optional[dict]:
        """Get cached value if not expired."""
        entry = self._cache_data.get(key)
        if entry:
            if time.time() - entry.get('timestamp', 0) < _SESSION_CACHE_TTL:
                logger.debug(f"Cache hit for {key}")
                return entry.get('value')
            else:
                # Remove expired entry
                del self._cache_data[key]
                self._save_cache()
        return None
    
    def set(self, key: str, value: dict) -> None:
        """Set cached value with timestamp."""
        self._cache_data[key] = {
            'value': value,
            'timestamp': time.time()
        }
        self._save_cache()
        logger.debug(f"Cache set for {key}")
    
    def set_rate_limit(self) -> None:
        """Mark that we hit a rate limit."""
        self._last_rate_limit_time = time.time()
        logger.warning("Rate limit hit, entering cooldown")
    
    def is_in_rate_limit_cooldown(self) -> bool:
        """Check if we're in rate limit cooldown."""
        return time.time() - self._last_rate_limit_time < _RATE_LIMIT_COOLDOWN
    
    def invalidate(self, key: str) -> None:
        """Invalidate a specific cache entry."""
        if key in self._cache_data:
            del self._cache_data[key]
            self._save_cache()
            logger.debug(f"Cache invalidated for {key}")
    
    def clear_all(self) -> None:
        """Clear all cache entries."""
        self._cache_data = {}
        self._save_cache()
        logger.debug("All cache cleared")

# Global cache instance
_cache: Optional[SessionCache] = None

def get_session_cache() -> SessionCache:
    """Get the global session cache instance."""
    global _cache
    if _cache is None:
        _cache = SessionCache()
    return _cache

def clear_session_cache() -> None:
    """Clear the global session cache."""
    global _cache
    if _cache is not None:
        _cache.clear_all()
