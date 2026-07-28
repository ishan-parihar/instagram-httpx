"""
Instagram account action tools.

Provides follow/unfollow, like/unlike, save, and comment actions
with destructive annotations for client-side confirmation prompts.
"""

import logging
from typing import Any

from fastmcp import Context, FastMCP
from fastmcp.dependencies import CurrentContext

from instagram_mcp_server.constants import TOOL_TIMEOUT_SECONDS
from instagram_mcp_server.dependencies import get_ready_extractor
from instagram_mcp_server.tools._guard import tool_guard

logger = logging.getLogger(__name__)


def register_action_tools(mcp: FastMCP) -> None:
    """Register all action-related tools with the MCP server."""

    @mcp.tool(
        timeout=TOOL_TIMEOUT_SECONDS,
        title="Follow User",
        annotations={"destructiveHint": True, "openWorldHint": True},
        tags={"actions", "social"},
    )
    @tool_guard("follow_user")
    async def follow_user(
        username: str,
        account_id: str | None = None,
        ctx: Context = CurrentContext(),
    ) -> dict[str, Any]:
        """
        Follow a user or send a follow request for private accounts.

        Navigates to the user's profile and clicks the Follow button.
        For private accounts, a follow request is sent.

        Args:
            username: Instagram username to follow (e.g., "natgeo")
            account_id: Optional account ID to use for the request

        Returns:
            Dict with url, status, and optional message.
        """
        extractor = await get_ready_extractor(ctx, tool_name="follow_user", account_id=account_id)
        logger.info("Following user: %s", username)

        result = await extractor.follow_user(
            username,
        )

        return result

    @mcp.tool(
        timeout=TOOL_TIMEOUT_SECONDS,
        title="Unfollow User",
        annotations={"destructiveHint": True, "openWorldHint": True},
        tags={"actions", "social"},
    )
    @tool_guard("unfollow_user")
    async def unfollow_user(
        username: str,
        account_id: str | None = None,
        ctx: Context = CurrentContext(),
    ) -> dict[str, Any]:
        """
        Unfollow a user.

        Navigates to the user's profile and clicks the Unfollow button.

        Args:
            username: Instagram username to unfollow (e.g., "natgeo")
            account_id: Optional account ID to use for the request

        Returns:
            Dict with url, status, and optional message.
        """
        extractor = await get_ready_extractor(ctx, tool_name="unfollow_user", account_id=account_id)
        logger.info("Unfollowing user: %s", username)

        result = await extractor.unfollow_user(
            username,
        )

        return result

    @mcp.tool(
        timeout=TOOL_TIMEOUT_SECONDS,
        title="Like Post",
        annotations={"destructiveHint": True, "openWorldHint": True},
        tags={"actions", "social"},
    )
    @tool_guard("like_post")
    async def like_post(
        post_url: str,
        account_id: str | None = None,
        ctx: Context = CurrentContext(),
    ) -> dict[str, Any]:
        """
        Like a post.

        Navigates to the post and clicks the Like button.

        Args:
            post_url: Instagram post URL (e.g., "https://www.instagram.com/p/ABC123/")
            account_id: Optional account ID to use for the request

        Returns:
            Dict with url, status, and optional message.
        """
        extractor = await get_ready_extractor(ctx, tool_name="like_post", account_id=account_id)
        logger.info("Liking post: %s", post_url)

        result = await extractor.like_post(post_url)

        return result

    @mcp.tool(
        timeout=TOOL_TIMEOUT_SECONDS,
        title="Unlike Post",
        annotations={"destructiveHint": True, "openWorldHint": True},
        tags={"actions", "social"},
    )
    @tool_guard("unlike_post")
    async def unlike_post(
        post_url: str,
        account_id: str | None = None,
        ctx: Context = CurrentContext(),
    ) -> dict[str, Any]:
        """
        Unlike a post.

        Navigates to the post and clicks the Unlike button.

        Args:
            post_url: Instagram post URL (e.g., "https://www.instagram.com/p/ABC123/")
            account_id: Optional account ID to use for the request

        Returns:
            Dict with url, status, and optional message.
        """
        extractor = await get_ready_extractor(ctx, tool_name="unlike_post", account_id=account_id)
        logger.info("Unliking post: %s", post_url)

        result = await extractor.unlike_post(post_url)

        return result

    @mcp.tool(
        timeout=TOOL_TIMEOUT_SECONDS,
        title="Save Post",
        annotations={"destructiveHint": True, "openWorldHint": True},
        tags={"actions"},
    )
    @tool_guard("save_post")
    async def save_post(
        post_url: str,
        collection: str | None = None,
        account_id: str | None = None,
        ctx: Context = CurrentContext(),
    ) -> dict[str, Any]:
        """
        Save a post to a collection.

        Navigates to the post and clicks the Save button.
        Optionally saves to a specific collection.

        Args:
            post_url: Instagram post URL (e.g., "https://www.instagram.com/p/ABC123/")
            collection: Optional collection name to save the post into
            account_id: Optional account ID to use for the request

        Returns:
            Dict with url, status, and optional message.
        """
        extractor = await get_ready_extractor(ctx, tool_name="save_post", account_id=account_id)
        logger.info(
            "Saving post: %s (collection=%s)",
            post_url,
            collection,
        )

        result = await extractor.save_post(post_url, collection or "")

        return result

    @mcp.tool(
        timeout=TOOL_TIMEOUT_SECONDS,
        title="Comment on Post",
        annotations={"destructiveHint": True, "openWorldHint": True},
        tags={"actions", "social"},
    )
    @tool_guard("comment_on_post")
    async def comment_on_post(
        post_url: str,
        comment: str,
        confirm_post: bool,
        account_id: str | None = None,
        ctx: Context = CurrentContext(),
    ) -> dict[str, Any]:
        """
        Post a comment on a post.

        Navigates to the post and submits the comment. confirm_post
        must be True for the comment to be posted.

        Args:
            post_url: Instagram post URL (e.g., "https://www.instagram.com/p/ABC123/")
            comment: The comment text to post
            confirm_post: Must be True to actually post the comment
            account_id: Optional account ID to use for the request

        Returns:
            Dict with url, status, and optional message.
        """
        if not confirm_post:
            return {
                "url": post_url,
                "status": "cancelled",
                "message": "Comment not posted. Set confirm_post=True to post.",
            }

        extractor = await get_ready_extractor(ctx, tool_name="comment_on_post", account_id=account_id)
        logger.info("Commenting on post: %s", post_url)

        result = await extractor.comment_on_post(post_url, comment)

        return result
