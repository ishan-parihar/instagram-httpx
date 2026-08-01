"""
Instagram-specific ObscuraCookieManager integration.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any, Optional

from obscura_core import (
    ObscuraCookieManager,
    FileCookieStorage,
    BrowserCookie3Extractor,
    CookieSource,
    CookieValidationResult,
    ReLoginRequiredError,
)

# Wrapper to add domain attribute to BrowserCookie3Extractor
class BrowserCookie3ExtractorWithDomain:
    """Wrapper around BrowserCookie3Extractor that adds domain attribute."""
    
    def __init__(self, browser_name: str, domain: str):
        self._extractor = BrowserCookie3Extractor(browser_name=browser_name)
        self.domain = domain
        self.name = browser_name
    
    async def extract(self, domain: str, required_cookies: list[str]):
        """Extract cookies using the wrapped extractor."""
        return await self._extractor.extract(domain, required_cookies)
    
    def is_available(self) -> bool:
        """Check if the extractor is available."""
        return self._extractor.is_available()

logger = logging.getLogger(__name__)

# Required cookies for Instagram
INSTAGRAM_REQUIRED_COOKIES = ["sessionid", "csrftoken"]


class InstagramCookieValidator:
    """Validates Instagram cookies by making an API call."""

    def __init__(self):
        self._session = None

    async def validate(self, cookies: dict[str, str]) -> bool:
        """Validate cookies by checking required cookies are present."""
        try:
            # For now, just check that required cookies are present
            # Full API validation can be added later
            required = ["sessionid", "csrftoken"]
            for cookie in required:
                if cookie not in cookies or not cookies[cookie]:
                    logger.debug(f"Required cookie missing: {cookie}")
                    return False
            return True
        except Exception as e:
            logger.debug(f"Instagram cookie validation failed: {e}")
            return False


class InstagramObscuraManager:
    """Instagram-specific wrapper around ObscuraCookieManager."""

    def __init__(self):
        self._manager: Optional[ObscuraCookieManager] = None
        self._validator = InstagramCookieValidator()

    def _get_storage(self) -> FileCookieStorage:
        """Get file-based cookie storage."""
        cookie_path = Path.home() / ".instagram-lyr" / "cookies.json"
        cookie_path.parent.mkdir(parents=True, exist_ok=True)
        return FileCookieStorage(cookie_path)

    def _get_extractor(self) -> BrowserCookie3ExtractorWithDomain:
        """Get browser cookie extractor (prefers Chrome)."""
        return BrowserCookie3ExtractorWithDomain(
            browser_name="chrome",
            domain="instagram.com"
        )

    def _get_manager(self) -> ObscuraCookieManager:
        """Get or create the ObscuraCookieManager instance."""
        if self._manager is None:
            self._manager = ObscuraCookieManager(
                storage=self._get_storage(),
                extractor=self._get_extractor(),
                validator=self._validator.validate,
                required_cookies=INSTAGRAM_REQUIRED_COOKIES,
                validation_interval=300,  # 5 minutes
                max_re_extraction_attempts=3,
                re_extraction_cooldown=60,
            )
        return self._manager

    async def get_valid_cookies(self, force_refresh: bool = False) -> CookieValidationResult:
        """Get valid cookies, performing validation and re-extraction as needed."""
        manager = self._get_manager()
        return await manager.get_cookies(force_refresh=force_refresh)

    async def force_re_extraction(self) -> CookieValidationResult:
        """Force re-extraction from browser (call after user logs in)."""
        manager = self._get_manager()
        return await manager.force_re_extraction()

    async def invalidate_and_trigger_relogin(self) -> None:
        """Invalidate auth and trigger re-login flow."""
        manager = self._get_manager()
        await manager.invalidate_and_trigger_relogin()

    def is_cache_valid(self) -> bool:
        """Check if cached cookies are within validation interval."""
        manager = self._get_manager()
        return manager.is_cache_valid()


# Global instance
_instagram_obscura_manager: Optional[InstagramObscuraManager] = None


def get_instagram_obscura_manager() -> InstagramObscuraManager:
    """Get the global Instagram Obscura manager instance."""
    global _instagram_obscura_manager
    if _instagram_obscura_manager is None:
        _instagram_obscura_manager = InstagramObscuraManager()
    return _instagram_obscura_manager


async def get_valid_instagram_cookies(force_refresh: bool = False) -> CookieValidationResult:
    """Get valid Instagram cookies using ObscuraCookieManager."""
    manager = get_instagram_obscura_manager()
    return await manager.get_valid_cookies(force_refresh)


async def force_instagram_cookie_refresh() -> CookieValidationResult:
    """Force re-extraction of Instagram cookies from browser."""
    manager = get_instagram_obscura_manager()
    return await manager.force_re_extraction()


async def invalidate_instagram_auth() -> None:
    """Invalidate Instagram auth and trigger re-login."""
    manager = get_instagram_obscura_manager()
    await manager.invalidate_and_trigger_relogin()