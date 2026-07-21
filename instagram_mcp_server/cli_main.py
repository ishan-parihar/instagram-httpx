"""Instagram MCP Server main CLI application entry point."""
import json

import asyncio
import sys

import httpx

from instagram_mcp_server.authentication import clear_auth_state
from instagram_mcp_server.config import get_config
from instagram_mcp_server.drivers.browser import (
    close_browser,
    get_profile_dir,
    load_cookies,
    profile_exists,
)
from instagram_mcp_server.logging_config import (
    configure_logging,
    teardown_trace_logging,
)
from instagram_mcp_server.server import create_mcp_server
from instagram_mcp_server.session_state import (
    get_runtime_id,
    load_source_state,
    portable_cookie_path,
    source_state_path,
)
from instagram_mcp_server.setup import run_profile_creation


def clear_profile_and_exit() -> None:
    """Clear Instagram profile and exit."""
    config = get_config()
    configure_logging(
        log_level=config.server.log_level,
        json_format=not config.is_interactive and config.server.log_level != "DEBUG",
    )

    profile_dir = get_profile_dir()
    if not (
        profile_exists(profile_dir)
        or portable_cookie_path(profile_dir).exists()
        or source_state_path(profile_dir).exists()
    ):
        print(json.dumps({"status": "nothing_to_clear", "message": "No authentication state found"}))
        sys.exit(0)

    if clear_auth_state(profile_dir):
        print(json.dumps({"status": "success", "message": "Authentication state cleared"}))
    else:
        print(json.dumps({"status": "error", "message": "Failed to clear authentication state"}))
        sys.exit(1)
    sys.exit(0)


def get_profile_and_exit() -> None:
    """Create profile interactively and exit."""
    config = get_config()
    configure_logging(
        log_level=config.server.log_level,
        json_format=not config.is_interactive and config.server.log_level != "DEBUG",
    )

    profile_dir = get_profile_dir()
    browser_id = config.cookie.preferred_browser
    success = run_profile_creation(str(profile_dir), browser_id=browser_id)
    sys.exit(0 if success else 1)


def profile_info_and_exit() -> None:
    """Check profile validity and display info, then exit."""
    config = get_config()
    configure_logging(
        log_level=config.server.log_level,
        json_format=not config.is_interactive and config.server.log_level != "DEBUG",
    )

    profile_dir = get_profile_dir()
    cookies_path = portable_cookie_path(profile_dir)
    source_state = load_source_state(profile_dir)
    if not source_state or not profile_exists(profile_dir) or not cookies_path.exists():
        print(json.dumps({"status": "error", "message": f"No valid source session at {profile_dir}", "help": "Run with --login to create a source session"}))
        sys.exit(1)

    out = {"profile_dir": str(profile_dir), "runtime_id": get_runtime_id()}
    if source_state:
        out["source_runtime"] = source_state.source_runtime_id
        out["login_generation"] = source_state.login_generation

    valid = asyncio.run(_check_session_api())

    if valid:
        out["status"] = "valid"
        print(json.dumps(out))
        sys.exit(0)

    out["status"] = "expired"
    out["help"] = "Run with --login to re-authenticate"
    print(json.dumps(out))
    sys.exit(1)


async def _check_session_api() -> bool:
    """Check Instagram session validity by calling the web profile API."""
    try:
        cookies = load_cookies()
        if not cookies:
            return False

        headers = {
            "X-CSRFToken": cookies.get("csrftoken", ""),
            "X-IG-App-ID": "936619743392459",
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"
            ),
        }
        async with httpx.AsyncClient(
            cookies=cookies, headers=headers, timeout=15
        ) as client:
            resp = await client.get(
                "https://www.instagram.com/api/v1/users/web_profile_info/"
                "?username=instagram"
            )
            data = resp.json()
            return resp.status_code == 200 and data.get("status") == "ok"
    except Exception:
        return False


def get_version() -> str:
    try:
        from importlib.metadata import PackageNotFoundError, version

        for package_name in ("instagram-scraper-mcp", "instagram-mcp-server"):
            try:
                return version(package_name)
            except PackageNotFoundError:
                continue
    except Exception:
        pass
    try:
        import os
        import tomllib

        pyproject_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "pyproject.toml"
        )
        with open(pyproject_path, "rb") as f:
            data = tomllib.load(f)
            return data["project"]["version"]
    except Exception:
        return "unknown"


def main() -> None:
    """Main application entry point."""
    config = get_config()

    configure_logging(
        log_level=config.server.log_level,
        json_format=not config.is_interactive and config.server.log_level != "DEBUG",
    )

    version = get_version()

    if config.is_interactive:
        print(json.dumps({"bin": "instagram-httpx-mcp", "version": version, "description": "Instagram MCP server with browser automation"}))

    # Handle --list-tools flag (AXI §8 content-first)
    if config.server.list_tools:
        list_tools_and_exit()

    # Handle --tool-info flag (AXI §9 contextual disclosure)
    if config.server.tool_info:
        tool_info_and_exit(config.server.tool_info)

    try:
        # Handle --logout flag
        if config.server.logout:
            clear_profile_and_exit()

        # Handle --login flag
        if config.server.login:
            get_profile_and_exit()

        # Handle --status flag
        if config.server.status:
            profile_info_and_exit()

        try:
            transport = config.server.transport

            # AXI §6: No interactive prompts — use --transport flag instead

            mcp = create_mcp_server()

            if transport == "streamable-http":
                mcp.run(
                    transport=transport,
                    host=config.server.host,
                    port=config.server.port,
                    path=config.server.path,
                )
            else:
                mcp.run(transport=transport)

        except KeyboardInterrupt:
            exit_gracefully(0)
        except Exception as e:
            print(json.dumps({"error": f"Server runtime error: {e}"}))
            exit_gracefully(1)
    finally:
        teardown_trace_logging(keep_traces=False)


def exit_gracefully(exit_code: int = 0) -> None:
    try:
        asyncio.run(close_browser())
    except Exception:
        pass
    sys.exit(exit_code)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        exit_gracefully(0)
    except Exception as e:
        print(json.dumps({"error": f"Error running MCP server: {e}"}))
        exit_gracefully(1)


def list_tools_and_exit() -> None:
    """List all available MCP tools and exit (AXI §8 content-first)."""
    tools = [
        ("ias_get_user_profile", "Get Instagram user profile information"),
        ("ias_get_user_stories", "Get user's active stories"),
        ("ias_get_user_highlights", "Get user's highlight reels"),
        ("ias_get_media_feed", "Get user's media feed"),
        ("ias_get_media_detail", "Get detailed info for a specific post"),
        ("ias_get_media_comments", "Get comments on a post"),
        ("ias_get_user_reels", "Get user's Reels videos"),
        ("ias_search_users", "Search for Instagram users"),
        ("ias_get_followers", "Get user's followers list"),
        ("ias_get_following", "Get user's following list"),
        ("ias_send_direct_message", "Send a direct message to a user"),
        ("ias_get_direct_messages", "Get direct message threads"),
        ("ias_create_post_container", "Create a media container for posting"),
        ("ias_publish_media", "Publish a media container to feed"),
        ("ias_like_media", "Like a post"),
        ("ias_comment_on_media", "Comment on a post"),
    ]
    print(f"tools[{len(tools)}]{{name,description}}:")
    for name, desc in tools:
        print(f"  {name},{desc}")
    print()
    print("help[2]:")
    print("  Run `instagram-httpx-mcp --tool-info <name>` for details")
    print("  Run `instagram-httpx-mcp` to start the MCP server")
    sys.exit(0)


def axi_error(msg: str, hint: str = None) -> None:
    """Print structured error to stdout (AXI §6) and exit with code 2."""
    out = {"error": msg}
    if hint:
        out["help"] = hint
    print(json.dumps(out))
    sys.exit(2)


def tool_info_and_exit(tool_name: str) -> None:
    """Show detailed info for a specific tool (AXI S9 contextual disclosure)."""
    tools_info = {
        "ias_get_user_profile": {
            "name": "ias_get_user_profile",
            "description": "Get Instagram user profile information by username",
            "parameters": {"username": "string (required)", "sections": "string (optional, comma-separated: posts,reels,tagged,followers,following)"},
            "returns": "Profile data including bio, followers, following, and optional sections",
        },
        "ias_get_user_stories": {
            "name": "ias_get_user_stories",
            "description": "Get user active stories",
            "parameters": {"username": "string (required)"},
            "returns": "Array of story objects with media_url, timestamp, expires_at",
        },
        "ias_get_user_highlights": {
            "name": "ias_get_user_highlights",
            "description": "Get user story highlight reels",
            "parameters": {"username": "string (required)"},
            "returns": "Array of highlight objects with title, cover_url, highlight_id",
        },
        "ias_get_media_feed": {
            "name": "ias_get_media_feed",
            "description": "Get user media feed posts",
            "parameters": {"username": "string (required)", "max_posts": "number (default 50)"},
            "returns": "Array of media objects with id, shortcode, url, thumbnail, media_type",
        },
        "ias_get_media_detail": {
            "name": "ias_get_media_detail",
            "description": "Get detailed info for a specific post",
            "parameters": {"post_url": "string (required)", "include_comments": "boolean (default false)"},
            "returns": "Post details with caption, engagement, media URLs, location, tags",
        },
        "ias_get_media_comments": {
            "name": "ias_get_media_comments",
            "description": "Get comments on a post",
            "parameters": {"post_url": "string (required)", "limit": "number (default 50)"},
            "returns": "Array of comment objects with author, text, timestamp",
        },
        "ias_get_user_reels": {
            "name": "ias_get_user_reels",
            "description": "Get user Reels videos",
            "parameters": {"username": "string (required)", "max_reels": "number (default 50)"},
            "returns": "Array of reel objects with id, shortcode, url, thumbnail, view_count",
        },
        "ias_search_users": {
            "name": "ias_search_users",
            "description": "Search for Instagram users",
            "parameters": {"query": "string (required)", "max_results": "number (default 50)"},
            "returns": "Array of user objects with username, full_name, profile_pic_url",
        },
        "ias_get_followers": {
            "name": "ias_get_followers",
            "description": "Get user followers list",
            "parameters": {"username": "string (required)"},
            "returns": "Array of follower objects with username, full_name",
        },
        "ias_get_following": {
            "name": "ias_get_following",
            "description": "Get user following list",
            "parameters": {"username": "string (required)"},
            "returns": "Array of following objects with username, full_name",
        },
        "ias_send_direct_message": {
            "name": "ias_send_direct_message",
            "description": "Send a direct message to a user",
            "parameters": {"username": "string (required)", "message": "string (required)", "confirm_send": "boolean (required, must be true)"},
            "returns": "Status object with sent flag and message confirmation",
        },
        "ias_get_direct_messages": {
            "name": "ias_get_direct_messages",
            "description": "Get direct message threads",
            "parameters": {"username": "string (optional)", "thread_id": "string (optional)", "limit": "number (default 50)"},
            "returns": "Array of message objects with sender, text, timestamp",
        },
        "ias_create_post_container": {
            "name": "ias_create_post_container",
            "description": "Create a media container for posting",
            "parameters": {"caption": "string (required)", "media_url": "string (required)"},
            "returns": "Container ID for publishing",
        },
        "ias_publish_media": {
            "name": "ias_publish_media",
            "description": "Publish a media container to feed",
            "parameters": {"container_id": "string (required)"},
            "returns": "Published post status with post URL",
        },
        "ias_like_media": {
            "name": "ias_like_media",
            "description": "Like a post",
            "parameters": {"post_url": "string (required)"},
            "returns": "Status object with like confirmation",
        },
        "ias_comment_on_media": {
            "name": "ias_comment_on_media",
            "description": "Comment on a post",
            "parameters": {"post_url": "string (required)", "comment": "string (required)", "confirm_post": "boolean (required, must be true)"},
            "returns": "Status object with comment confirmation",
        },
    }
    if tool_name in tools_info:
        print(json.dumps(tools_info[tool_name], indent=2))
    else:
        valid = list(tools_info.keys())
        axi_error(f"Unknown tool: '{tool_name}'", f"Valid tools: {', '.join(valid)}")
    sys.exit(0)
