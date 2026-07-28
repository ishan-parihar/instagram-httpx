"""Dependency injection for MCP tools — creates an API client from saved cookies."""

from __future__ import annotations

import json
import logging
from typing import Any, NoReturn

from fastmcp import Context

from instagram_mcp_server.bootstrap import (
    ensure_tool_ready_or_raise,
    invalidate_auth_and_trigger_relogin,
)
from instagram_mcp_server.core.exceptions import AuthenticationError
from instagram_mcp_server.drivers.browser import get_profile_dir
from instagram_mcp_server.error_handler import raise_tool_error
from instagram_mcp_server.scraping import InstagramAPIClient

logger = logging.getLogger(__name__)


async def handle_auth_error(
    error: AuthenticationError,
    ctx: Context | None,
) -> NoReturn:
    """Trigger interactive re-login."""
    logger.warning("Stale session detected; triggering re-login")
    await invalidate_auth_and_trigger_relogin(ctx)


async def get_ready_extractor(
    ctx: Context | None,
    *,
    tool_name: str,
    account_id: str | None = None,
) -> InstagramAPIClient:
    """Run bootstrap gating, then create an authenticated API client.
    
    Args:
        ctx: MCP context
        tool_name: Name of the tool being executed
        account_id: Optional account ID to use for cookie loading
    
    Returns:
        Authenticated InstagramAPIClient instance
    """
    try:
        await ensure_tool_ready_or_raise(tool_name, ctx)
        client = _build_api_client(account_id=account_id)
        return client
    except AuthenticationError as e:
        await handle_auth_error(e, ctx)
    except Exception as e:
        raise_tool_error(e, tool_name)


def _build_api_client(account_id: str | None = None) -> InstagramAPIClient:
    """Load cookies from disk and return an :class:`InstagramAPIClient`.
    
    Args:
        account_id: Optional account ID to load cookies for. If not provided,
                   uses the default/active account or falls back to legacy cookie loading.
    
    Returns:
        Authenticated InstagramAPIClient instance
    """
    # Try multi-account cookies first if account_id is specified
    if account_id:
        from instagram_mcp_server.multi_account import get_account_cookies
        
        cookies = get_account_cookies(account_id)
        if cookies:
            logger.info(
                "API client created from account %s (%d cookies)",
                account_id,
                len(cookies),
            )
            return InstagramAPIClient(cookies)
        else:
            logger.warning(f"Account {account_id} not found, falling back to default")
    
    # Try active account if no account_id specified
    if not account_id:
        from instagram_mcp_server.multi_account import get_active_account, get_account_cookies
        
        active_account = get_active_account()
        if active_account:
            cookies = get_account_cookies(active_account.account_id)
            if cookies:
                logger.info(
                    "API client created from active account %s (%d cookies)",
                    active_account.account_id,
                    len(cookies),
                )
                return InstagramAPIClient(cookies)
    
    # Fallback to legacy cookie loading
    profile_dir = get_profile_dir()
    cookie_file = profile_dir / "cookies.json"

    if not cookie_file.exists():
        # Fallback to session_state portable path
        from instagram_mcp_server.session_state import portable_cookie_path

        cookie_file = portable_cookie_path(profile_dir)
        if not cookie_file.exists():
            raise AuthenticationError(
                "No Instagram session found. Run with --login to create one."
            )

    raw = json.loads(cookie_file.read_text())

    # Support both list-of-dicts and dict-from-firefox formats
    if isinstance(raw, list):
        cookies = {c["name"]: c["value"] for c in raw if "name" in c and "value" in c}
    elif isinstance(raw, dict):
        cookies = raw
    else:
        cookies = {}

    if "sessionid" not in cookies:
        raise AuthenticationError(
            "Saved cookies are missing sessionid. Run with --login to re-authenticate."
        )

    logger.info(
        "API client created from %s (%d cookies)",
        cookie_file,
        len(cookies),
    )
    return InstagramAPIClient(cookies)


async def get_ready_posting_client(
    ctx: Context | None,
    *,
    tool_name: str,
    account_id: str | None = None,
) -> Any:
    """Get a posting client for media upload operations.
    
    Args:
        ctx: MCP context
        tool_name: Name of the tool being executed
        account_id: Optional account ID to use for cookie loading
    
    Returns:
        Authenticated PostingClient instance
    
    Raises:
        AuthenticationError: If session is invalid
        Exception: For other errors
    """
    try:
        from instagram_mcp_server.posting.client import PostingClient
        
        await ensure_tool_ready_or_raise(tool_name, ctx)
        client = PostingClient(account_id=account_id)
        return client
    except AuthenticationError as e:
        await handle_auth_error(e, ctx)
    except Exception as e:
        raise_tool_error(e, tool_name)
