"""
Instagram-specific Obscura Daemon plugin integration.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

from obscura_core import ObscuraPlugin, CookieValidationResult

logger = logging.getLogger(__name__)

# Required cookies for Instagram
INSTAGRAM_REQUIRED_COOKIES = ["sessionid", "csrftoken"]


class InstagramDaemonManager:
    """Instagram-specific wrapper around Obscura Daemon plugin."""

    def __init__(self, daemon_url: str = "http://127.0.0.1:9999"):
        self.daemon_url = daemon_url
        self._plugin: Optional[ObscuraPlugin] = None
        self._use_daemon = os.getenv("INSTAGRAM_USE_DAEMON", "true").lower() in ("1", "true", "yes", "on")

    async def _get_plugin(self) -> ObscuraPlugin:
        """Get or create the ObscuraPlugin instance."""
        if self._plugin is None:
            self._plugin = ObscuraPlugin(daemon_url=self.daemon_url)
            await self._plugin.connect()
        return self._plugin

    async def get_valid_cookies(self, force_refresh: bool = False) -> CookieValidationResult:
        """Get valid cookies from daemon cache."""
        if not self._use_daemon:
            logger.debug("Daemon integration disabled, falling back to local ObscuraCookieManager")
            # Import here to avoid circular imports
            from instagram_mcp_server.obscura_integration import get_valid_instagram_cookies
            return await get_valid_instagram_cookies(force_refresh)

        try:
            plugin = await self._get_plugin()

            if force_refresh:
                # Trigger sync to refresh cache
                await plugin.sync_cookies("instagram")

            cookies = await plugin.get_cookies("instagram")

            if cookies is None:
                logger.warning("No cookies found in daemon cache for instagram")
                return CookieValidationResult(
                    valid=False,
                    source="daemon",
                    cookies={},
                    error="No cookies found in daemon cache",
                )

            # Validate required cookies
            for cookie in INSTAGRAM_REQUIRED_COOKIES:
                if cookie not in cookies or not cookies[cookie]:
                    logger.debug(f"Required cookie missing: {cookie}")
                    return CookieValidationResult(
                        valid=False,
                        source="daemon",
                        cookies=cookies,
                        error=f"Required cookie missing: {cookie}",
                    )

            return CookieValidationResult(
                valid=True,
                cookies=cookies,
                source="daemon",
            )
        except Exception as e:
            logger.error(f"Error getting cookies from daemon: {e}")
            # Fall back to local ObscuraCookieManager
            logger.debug("Falling back to local ObscuraCookieManager")
            from instagram_mcp_server.obscura_integration import get_valid_instagram_cookies
            return await get_valid_instagram_cookies(force_refresh)

    async def close(self) -> None:
        """Close the plugin connection."""
        if self._plugin:
            await self._plugin.close()
            self._plugin = None


# Global instance
_instagram_daemon_manager: Optional[InstagramDaemonManager] = None


def get_instagram_daemon_manager(daemon_url: str = "http://127.0.0.1:9999") -> InstagramDaemonManager:
    """Get the global Instagram Daemon manager instance."""
    global _instagram_daemon_manager
    if _instagram_daemon_manager is None:
        _instagram_daemon_manager = InstagramDaemonManager(daemon_url=daemon_url)
    return _instagram_daemon_manager


async def get_valid_instagram_cookies_from_daemon(force_refresh: bool = False) -> CookieValidationResult:
    """Get valid Instagram cookies using Obscura Daemon plugin."""
    manager = get_instagram_daemon_manager()
    return await manager.get_valid_cookies(force_refresh)
