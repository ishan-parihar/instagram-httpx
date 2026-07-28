"""
Instagram post scraping tools.

Uses innerText extraction for resilient post data capture
with support for individual posts and locations.
"""

import logging
from typing import Any

from fastmcp import Context, FastMCP
from fastmcp.dependencies import CurrentContext

from instagram_mcp_server.constants import TOOL_TIMEOUT_SECONDS
from instagram_mcp_server.dependencies import get_ready_extractor
from instagram_mcp_server.tools._guard import tool_guard

logger = logging.getLogger(__name__)


def register_post_tools(mcp: FastMCP) -> None:
    """Register all post-related tools with the MCP server."""

    @mcp.tool(
        timeout=TOOL_TIMEOUT_SECONDS,
        title="Get Post Details",
        annotations={"readOnlyHint": True, "openWorldHint": True},
        tags={"post", "scraping"},
    )
    @tool_guard("get_post_details")
    async def get_post_details(
        post_url: str,
        include_comments: bool = False,
        ctx: Context = CurrentContext(),
    ) -> dict[str, Any]:
        """
        Get detailed post/reel information with structured data.

        Returns structured data including:
        - id, shortcode, url
        - caption, timestamp
        - media_type (1=image, 2=video, 8=carousel)
        - media_url, video_url, thumbnail_url
        - engagement (likes, views, comments)
        - audio info (for reels)
        - location, usertags, sponsor_tags
        - carousel children
        - optional comments

        Args:
            post_url: Full Instagram post URL
            include_comments: Whether to include comments in the response

        Returns:
            Dict with post details from the Instagram API.
        """
        extractor = await get_ready_extractor(ctx, tool_name="get_post_details")

        logger.info(
            "Fetching post details: %s (include_comments=%s)",
            post_url,
            include_comments,
        )

        await ctx.report_progress(
            progress=0, total=100, message="Fetching post details"
        )

        result = await extractor.get_post_details(
            post_url, include_comments=include_comments
        )

        await ctx.report_progress(progress=100, total=100, message="Complete")

        return result

    @mcp.tool(
        timeout=TOOL_TIMEOUT_SECONDS,
        title="Get Location Posts",
        annotations={"readOnlyHint": True, "openWorldHint": True},
        tags={"post", "scraping", "location"},
    )
    @tool_guard("get_location_posts")
    async def get_location_posts(
        location_id: str,
        max_posts: int = 50,
        ctx: Context = CurrentContext(),
    ) -> dict[str, Any]:
        """
        Get posts tagged at a location.

        Extracts post links from the location grid page and returns them as
        structured references. Use `get_post_details` for individual post enrichment.

        Args:
            location_id: Instagram location ID
            max_posts: Maximum number of posts to load (default 50)

        Returns:
            Dict with url, sections (name -> raw text), references (post links),
            and total_posts count.
        """
        extractor = await get_ready_extractor(ctx, tool_name="get_location_posts")

        logger.info(
            "Fetching location posts: %s (max_posts=%s)",
            location_id,
            max_posts,
        )

        await ctx.report_progress(
            progress=0, total=100, message="Fetching location posts"
        )

        result = await extractor.get_location_posts(
            location_id, max_posts=max_posts
        )

        await ctx.report_progress(progress=100, total=100, message="Complete")

        return result

    @mcp.tool(
        timeout=TOOL_TIMEOUT_SECONDS,
        title="Get Hashtag Posts",
        annotations={"readOnlyHint": True, "openWorldHint": True},
        tags={"post", "scraping", "hashtag"},
    )
    @tool_guard("get_hashtag_posts")
    async def get_hashtag_posts(
        hashtag: str,
        max_posts: int = 50,
        ctx: Context = CurrentContext(),
    ) -> dict[str, Any]:
        """
        Get posts for a hashtag.

        Extracts post links from the hashtag grid page and returns them as
        structured references. Use `get_post_details` for individual post enrichment.

        Args:
            hashtag: Hashtag to search (without the # symbol)
            max_posts: Maximum number of posts to load (default 50)

        Returns:
            Dict with url, sections (name -> raw text), references (post links),
            and total_posts count.
        """
        extractor = await get_ready_extractor(ctx, tool_name="get_hashtag_posts")

        logger.info(
            "Fetching hashtag posts: %s (max_posts=%s)",
            hashtag,
            max_posts,
        )

        await ctx.report_progress(
            progress=0, total=100, message="Fetching hashtag posts"
        )

        result = await extractor.get_hashtag_posts(
            hashtag, max_posts=max_posts
        )

        await ctx.report_progress(progress=100, total=100, message="Complete")

        return result
