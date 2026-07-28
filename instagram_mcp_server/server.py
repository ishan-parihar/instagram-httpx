"""
FastMCP server implementation for Instagram integration with tool registration.

Creates and configures the MCP server with comprehensive Instagram tool suite including
person profiles, company data, job information, and session management capabilities.
"""

import logging
from typing import Any, AsyncIterator

from fastmcp import FastMCP
from fastmcp.server.lifespan import lifespan

from instagram_mcp_server.bootstrap import (
    get_runtime_policy,
    initialize_bootstrap,
)
from instagram_mcp_server.constants import TOOL_TIMEOUT_SECONDS
from instagram_mcp_server.drivers.browser import close_browser
from instagram_mcp_server.error_handler import raise_tool_error
from instagram_mcp_server.sequential_tool_middleware import (
    SequentialToolExecutionMiddleware,
)
from instagram_mcp_server.tools.user import register_user_tools
from instagram_mcp_server.tools.posts import register_post_tools as register_scraping_post_tools
from instagram_mcp_server.tools.search import register_search_tools
from instagram_mcp_server.tools.actions import register_action_tools
from instagram_mcp_server.tools.messaging import register_messaging_tools
from instagram_mcp_server.tools.posting_tools import register_posting_tools
from instagram_mcp_server.tools.multi_account_tools import register_multi_account_tools
from instagram_mcp_server.tools.feed_tools import register_feed_tools
from instagram_mcp_server.tools.trigger_tools import register_trigger_tools

logger = logging.getLogger(__name__)


@lifespan
async def api_lifespan(app: FastMCP) -> AsyncIterator[dict[str, Any]]:
    """Manage API lifecycle — no browser needed.

    All scraping is done through Instagram's private API via httpx.
    Cookie-based authentication is loaded on demand for each tool call.
    """
    del app
    logger.info("Instagram MCP Server starting...")
    initialize_bootstrap(get_runtime_policy())
    logger.info("API-only mode: no browser setup needed")

    yield {}

    logger.info("Instagram MCP Server shutting down...")


def create_mcp_server() -> FastMCP:
    """Create and configure the MCP server with all Instagram tools."""
    mcp = FastMCP(
        "instagram_httpx",
        lifespan=api_lifespan,
        mask_error_details=True,
    )
    mcp.add_middleware(SequentialToolExecutionMiddleware())

    # Register all tools
    register_user_tools(mcp)
    register_scraping_post_tools(mcp)
    register_messaging_tools(mcp)
    register_search_tools(mcp)
    register_action_tools(mcp)
    register_multi_account_tools(mcp)
    register_feed_tools(mcp)
    register_trigger_tools(mcp)
    register_posting_tools(mcp)

    # Optional tools removed - transcription and gemini analysis moved to external packages

    # Register session management tool
    @mcp.tool(
        timeout=TOOL_TIMEOUT_SECONDS,
        title="Close Session",
        annotations={"destructiveHint": True},
        tags={"session"},
    )
    async def close_session() -> dict[str, Any]:
        """Close the current Instagram browser session and clean up resources."""
        try:
            await close_browser()
            return {
                "status": "success",
                "message": "Successfully closed the browser session and cleaned up resources",
            }
        except Exception as e:
            raise_tool_error(e, "close_session")  # NoReturn

    return mcp
