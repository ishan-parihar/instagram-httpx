"""
Feed browsing tools for Instagram MCP Server.

Provides tools for AI agents to browse home feed, discover content,
and access timeline posts from followed accounts.
"""

import logging
from typing import Any

from fastmcp import Context, FastMCP
from fastmcp.dependencies import CurrentContext

from instagram_mcp_server.callbacks import MCPContextProgressCallback
from instagram_mcp_server.constants import TOOL_TIMEOUT_SECONDS
from instagram_mcp_server.dependencies import get_ready_extractor
from instagram_mcp_server.tools._guard import tool_guard
from instagram_mcp_server.feed import FeedBrowser

logger = logging.getLogger(__name__)


def register_feed_tools(mcp: FastMCP) -> None:
    """Register all feed browsing tools with the MCP server."""

    @mcp.tool(
        timeout=TOOL_TIMEOUT_SECONDS,
        title="Get Home Feed",
        annotations={"readOnlyHint": True, "openWorldHint": True},
        tags={"feed", "scraping"},
    )
    @tool_guard("get_home_feed")
    async def get_home_feed(
        max_posts: int = 50,
        account_id: str | None = None,
        ctx: Context = CurrentContext(),
    ) -> dict[str, Any]:
        """
        Get the home feed (posts from followed accounts).
        
        Args:
            max_posts: Maximum number of posts to retrieve (default 50)
            account_id: Optional account ID to use for the request
        
        Returns:
            Dict with feed data including posts list and metadata
        """
        extractor = await get_ready_extractor(ctx, tool_name="get_home_feed", account_id=account_id)
        
        logger.info("Fetching home feed (max_posts=%d)", max_posts)
        
        cb = MCPContextProgressCallback(ctx)
        feed_browser = FeedBrowser(extractor)
        result = await feed_browser.get_home_feed(max_posts=max_posts, callbacks=cb)
        
        return result

    @mcp.tool(
        timeout=TOOL_TIMEOUT_SECONDS,
        title="Get Discover Feed",
        annotations={"readOnlyHint": True, "openWorldHint": True},
        tags={"feed", "scraping"},
    )
    @tool_guard("get_discover_feed")
    async def get_discover_feed(
        max_posts: int = 50,
        account_id: str | None = None,
        ctx: Context = CurrentContext(),
    ) -> dict[str, Any]:
        """
        Get the discover/explore feed with trending content.
        
        Args:
            max_posts: Maximum number of posts to retrieve (default 50)
            account_id: Optional account ID to use for the request
        
        Returns:
            Dict with discover feed data including posts list
        """
        extractor = await get_ready_extractor(ctx, tool_name="get_discover_feed", account_id=account_id)
        
        logger.info("Fetching discover feed (max_posts=%d)", max_posts)
        
        cb = MCPContextProgressCallback(ctx)
        feed_browser = FeedBrowser(extractor)
        result = await feed_browser.get_discover_feed(max_posts=max_posts, callbacks=cb)
        
        return result

    @mcp.tool(
        timeout=TOOL_TIMEOUT_SECONDS,
        title="Get User Timeline",
        annotations={"readOnlyHint": True, "openWorldHint": True},
        tags={"feed", "scraping"},
    )
    @tool_guard("get_user_timeline")
    async def get_user_timeline(
        username: str,
        max_posts: int = 50,
        account_id: str | None = None,
        ctx: Context = CurrentContext(),
    ) -> dict[str, Any]:
        """
        Get recent posts from a specific user's timeline.
        
        Args:
            username: Instagram username to fetch timeline for
            max_posts: Maximum number of posts to retrieve (default 50)
            account_id: Optional account ID to use for the request
        
        Returns:
            Dict with user timeline data including posts list
        """
        extractor = await get_ready_extractor(ctx, tool_name="get_user_timeline", account_id=account_id)
        
        logger.info("Fetching user timeline for %s (max_posts=%d)", username, max_posts)
        
        cb = MCPContextProgressCallback(ctx)
        feed_browser = FeedBrowser(extractor)
        result = await feed_browser.get_user_timeline(
            username=username, 
            max_posts=max_posts, 
            callbacks=cb
        )
        
        return result