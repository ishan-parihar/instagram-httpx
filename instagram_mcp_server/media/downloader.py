"""Shared media download utility with cookie auth.

Media CDN fetches that (often) carry the session ``sessionid`` cookie are served
from the same Instagram frontend that the API hits, so they must use the SAME
coherent UA + TLS fingerprint as the API client. A mobile UA over a plain
httpx/curl TLS stack while the private API uses desktop Chrome is the exact
fingerprint inconsistency that gets sessions flagged.
"""

import logging
from pathlib import Path

from curl_cffi.requests import AsyncSession as _AsyncSession

from instagram_mcp_server.scraping import identity

logger = logging.getLogger(__name__)


def _session_headers(cookies: dict[str, str] | None) -> dict[str, str]:
    headers = {
        "Referer": "https://www.instagram.com/",
        "User-Agent": identity.USER_AGENT,
    }
    headers.update(identity.client_hints())
    if cookies:
        cookie_header = "; ".join(f"{k}={v}" for k, v in cookies.items() if v)
        if cookie_header:
            headers["Cookie"] = cookie_header
    return headers


async def download_media(
    media_url: str,
    output_path: str | Path,
    cookies: dict[str, str] | None = None,
    *,
    timeout: float = 60.0,
) -> bool:
    """
    Download media from Instagram CDN with cookie auth.

    Args:
        media_url: The CDN URL to download
        output_path: Where to save the file
        cookies: Instagram session cookies dict for auth
        timeout: Request timeout in seconds

    Returns:
        True if download succeeded, False otherwise
    """
    try:
        headers = _session_headers(cookies)
        async with _AsyncSession(
            impersonate=identity.IMPERSONATE, headers=headers, timeout=timeout,
        ) as client:
            async with client.stream("GET", media_url) as response:
                if response.status_code != 200:
                    logger.error("Download failed: HTTP %d for %s", response.status_code, media_url[:80])
                    return False
                output_path = Path(output_path)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, "wb") as f:
                    async for chunk in response.aiter_content():
                        f.write(chunk)
        logger.info("Downloaded: %s", output_path.name)
        return True
    except Exception as e:
        logger.error("Download error: %s", e)
        return False


async def download_bytes(
    media_url: str,
    cookies: dict[str, str] | None = None,
    *,
    timeout: float = 30.0,
) -> bytes | None:
    """
    Download media bytes (for in-memory processing like Gemini upload).

    Args:
        media_url: The CDN URL to download
        cookies: Instagram session cookies dict for auth
        timeout: Request timeout in seconds

    Returns:
        Raw bytes or None on failure
    """
    try:
        headers = _session_headers(cookies)
        async with _AsyncSession(
            impersonate=identity.IMPERSONATE, headers=headers, timeout=timeout,
        ) as client:
            response = await client.get(media_url)
            if response.status_code == 200:
                return response.content
            logger.warning("Download returned HTTP %d for %s", response.status_code, media_url[:80])
            return None
    except Exception as e:
        logger.error("Download error: %s", e)
        return None
