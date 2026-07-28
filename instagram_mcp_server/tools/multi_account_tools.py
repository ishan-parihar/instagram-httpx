"""
Multi-account management tools for Instagram MCP Server.

Provides tools for AI agents to manage multiple Instagram accounts,
switch between accounts, and perform account-specific operations.
"""

import logging
from typing import Any

from fastmcp import Context, FastMCP
from fastmcp.dependencies import CurrentContext

from instagram_mcp_server.constants import TOOL_TIMEOUT_SECONDS
from instagram_mcp_server.error_handler import raise_tool_error
from instagram_mcp_server.multi_account import (
    list_accounts,
    get_account,
    create_account,
    delete_account,
    set_account_cookies,
    get_active_account,
    set_default_account,
    update_account_last_used,
)
from instagram_mcp_server.cookie_import import extract_chromium_cookies, find_browser_cookie_db

logger = logging.getLogger(__name__)


def register_multi_account_tools(mcp: FastMCP) -> None:
    """Register all multi-account management tools with the MCP server."""

    @mcp.tool(
        timeout=TOOL_TIMEOUT_SECONDS,
        title="List Instagram Accounts",
        annotations={"readOnlyHint": True, "openWorldHint": True},
        tags={"account", "management"},
    )
    async def list_instagram_accounts(
        ctx: Context = CurrentContext(),
    ) -> dict[str, Any]:
        """
        List all configured Instagram accounts.
        
        Returns a list of account metadata including username, account ID,
        active status, and last used timestamp.
        """
        try:
            accounts = list_accounts()
            
            result = {
                "accounts": [
                    {
                        "account_id": acc.account_id,
                        "username": acc.username,
                        "full_name": acc.full_name,
                        "profile_pic_url": acc.profile_pic_url,
                        "is_active": acc.is_active,
                        "created_at": acc.created_at,
                        "last_used": acc.last_used,
                    }
                    for acc in accounts
                ],
                "total_accounts": len(accounts),
                "active_account": None,
            }
            
            # Set active account separately
            active = get_active_account()
            if active is not None:
                result["active_account"] = active.account_id
            
            return result
        except Exception as e:
            logger.error(f"Failed to list accounts: {e}")
            raise_tool_error(e, "list_instagram_accounts")

    @mcp.tool(
        timeout=TOOL_TIMEOUT_SECONDS,
        title="Add Instagram Account",
        annotations={"destructiveHint": True, "openWorldHint": True},
        tags={"account", "management"},
    )
    async def add_instagram_account(
        username: str,
        cookies: dict[str, str],
        full_name: str | None = None,
        profile_pic_url: str | None = None,
        set_as_active: bool = True,
        ctx: Context = CurrentContext(),
    ) -> dict[str, Any]:
        """
        Add a new Instagram account with session cookies.
        
        Args:
            username: Instagram username
            cookies: Dictionary of Instagram cookies (sessionid, csrftoken, etc.)
            full_name: Optional full name from profile
            profile_pic_url: Optional profile picture URL
            set_as_active: Whether to set this as the active account (default: True)
        
        Returns:
            Account metadata including the generated account ID
        """
        try:
            account = create_account(
                username=username,
                cookies=cookies,
                full_name=full_name,
                profile_pic_url=profile_pic_url,
            )
            
            if set_as_active:
                set_default_account(account.account_id)
            
            return {
                "success": True,
                "account_id": account.account_id,
                "username": account.username,
                "is_active": account.is_active,
                "message": f"Account {username} added successfully",
            }
        except Exception as e:
            logger.error(f"Failed to add account: {e}")
            raise_tool_error(e, "add_instagram_account")

    @mcp.tool(
        timeout=TOOL_TIMEOUT_SECONDS,
        title="Remove Instagram Account",
        annotations={"destructiveHint": True, "openWorldHint": True},
        tags={"account", "management"},
    )
    async def remove_instagram_account(
        account_id: str,
        ctx: Context = CurrentContext(),
    ) -> dict[str, Any]:
        """
        Remove an Instagram account configuration.
        
        Args:
            account_id: The account ID to remove
        
        Returns:
            Success status and message
        """
        try:
            account = get_account(account_id)
            if not account:
                return {
                    "success": False,
                    "message": f"Account {account_id} not found",
                }
            
            success = delete_account(account_id)
            
            if success:
                return {
                    "success": True,
                    "message": f"Account {account.username} removed successfully",
                }
            else:
                return {
                    "success": False,
                    "message": f"Failed to remove account {account.username}",
                }
        except Exception as e:
            logger.error(f"Failed to remove account: {e}")
            raise_tool_error(e, "remove_instagram_account")

    @mcp.tool(
        timeout=TOOL_TIMEOUT_SECONDS,
        title="Switch Active Account",
        annotations={"destructiveHint": False, "openWorldHint": True},
        tags={"account", "management"},
    )
    async def switch_active_account(
        account_id: str,
        ctx: Context = CurrentContext(),
    ) -> dict[str, Any]:
        """
        Switch the active Instagram account for operations.
        
        Args:
            account_id: The account ID to set as active
        
        Returns:
            Success status and active account info
        """
        try:
            account = get_account(account_id)
            if not account:
                return {
                    "success": False,
                    "message": f"Account {account_id} not found",
                }
            
            success = set_default_account(account_id)
            
            if success:
                update_account_last_used(account_id)
                return {
                    "success": True,
                    "active_account_id": account_id,
                    "username": account.username,
                    "message": f"Switched to account {account.username}",
                }
            else:
                return {
                    "success": False,
                    "message": f"Failed to switch to account {account.username}",
                }
        except Exception as e:
            logger.error(f"Failed to switch account: {e}")
            raise_tool_error(e, "switch_active_account")

    @mcp.tool(
        timeout=TOOL_TIMEOUT_SECONDS,
        title="Get Active Account",
        annotations={"readOnlyHint": True, "openWorldHint": True},
        tags={"account", "management"},
    )
    async def get_active_account_info(
        ctx: Context = CurrentContext(),
    ) -> dict[str, Any]:
        """
        Get information about the currently active Instagram account.
        
        Returns:
            Active account metadata or null if no account is set
        """
        try:
            account = get_active_account()
            
            if not account:
                return {
                    "active_account": None,
                    "message": "No active account configured",
                }
            
            return {
                "active_account": {
                    "account_id": account.account_id,
                    "username": account.username,
                    "full_name": account.full_name,
                    "profile_pic_url": account.profile_pic_url,
                    "is_active": account.is_active,
                    "created_at": account.created_at,
                    "last_used": account.last_used,
                },
            }
        except Exception as e:
            logger.error(f"Failed to get active account: {e}")
            raise_tool_error(e, "get_active_account_info")

    @mcp.tool(
        timeout=TOOL_TIMEOUT_SECONDS,
        title="Import Account from Browser",
        annotations={"destructiveHint": True, "openWorldHint": True},
        tags={"account", "management"},
    )
    async def import_account_from_browser(
        username: str,
        browser: str = "chrome",
        set_as_active: bool = True,
        ctx: Context = CurrentContext(),
    ) -> dict[str, Any]:
        """
        Import Instagram account cookies directly from a browser.
        
        Args:
            username: Instagram username for the account
            browser: Browser to import from (chrome, firefox, brave, edge, etc.)
            set_as_active: Whether to set this as the active account (default: True)
        
        Returns:
            Success status and account information
        """
        try:
            # Find browser cookie database
            cookie_db = find_browser_cookie_db(browser)
            if not cookie_db:
                return {
                    "success": False,
                    "message": f"Could not find cookie database for browser: {browser}",
                }
            
            # Extract cookies
            if browser in ["firefox", "librewolf", "waterfox", "zen", "floorp"]:
                from instagram_mcp_server.cookie_import import extract_firefox_cookies
                cookies = extract_firefox_cookies(cookie_db)
            else:
                cookies = extract_chromium_cookies(cookie_db)
            
            # Validate required cookies
            required_cookies = {"sessionid", "csrftoken"}
            missing = required_cookies - set(cookies.keys())
            if missing:
                return {
                    "success": False,
                    "message": f"Missing required cookies: {missing}",
                }
            
            # Create account
            account = create_account(
                username=username,
                cookies=cookies,
            )
            
            if set_as_active:
                set_default_account(account.account_id)
            
            return {
                "success": True,
                "account_id": account.account_id,
                "username": account.username,
                "cookies_found": list(cookies.keys()),
                "message": f"Account {username} imported from {browser}",
            }
        except Exception as e:
            logger.error(f"Failed to import account from browser: {e}")
            raise_tool_error(e, "import_account_from_browser")

    @mcp.tool(
        timeout=TOOL_TIMEOUT_SECONDS,
        title="Update Account Cookies",
        annotations={"destructiveHint": True, "openWorldHint": True},
        tags={"account", "management"},
    )
    async def update_account_cookies(
        account_id: str,
        cookies: dict[str, str],
        ctx: Context = CurrentContext(),
    ) -> dict[str, Any]:
        """
        Update cookies for an existing Instagram account.
        
        Useful for refreshing expired sessions without re-adding the account.
        
        Args:
            account_id: The account ID to update
            cookies: New cookie dictionary
        
        Returns:
            Success status
        """
        try:
            account = get_account(account_id)
            if not account:
                return {
                    "success": False,
                    "message": f"Account {account_id} not found",
                }
            
            success = set_account_cookies(account_id, cookies)
            
            if success:
                return {
                    "success": True,
                    "message": f"Cookies updated for account {account.username}",
                }
            else:
                return {
                    "success": False,
                    "message": f"Failed to update cookies for account {account.username}",
                }
        except Exception as e:
            logger.error(f"Failed to update account cookies: {e}")
            raise_tool_error(e, "update_account_cookies")