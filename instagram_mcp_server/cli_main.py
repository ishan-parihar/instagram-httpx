"""Instagram MCP Server main CLI application entry point."""
import json

import asyncio
import os
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

# ── TOON output helpers (AXI §1) ───────────────────────────────────────────

def axi_error(msg: str, hint: str | None = None) -> None:
    """Print structured error to stdout (AXI §6) and exit with code 2."""
    print(f"error: {msg}")
    if hint:
        print(f"help: {hint}")
    sys.exit(2)


def _truncate(s: str, max_chars: int = 500) -> str:
    """Truncate string with ellipsis and escape hatch (AXI §3)."""
    if len(s) <= max_chars:
        return s
    return f"{s[:max_chars]}...\n  ... (truncated, {len(s)} chars total)"


def _get_bin_path() -> str:
    """Get executable path with home dir collapsed to ~ (AXI §10)."""
    try:
        home = os.environ.get("HOME", "")
        exe = sys.argv[0] if sys.argv else "instagram-httpx-mcp"
        if home and exe.startswith(home):
            return exe.replace(home, "~", 1)
        return exe
    except Exception:
        return "instagram-httpx-mcp"


def toon_print_dict(data: dict, indent: int = 0) -> None:
    """Print dict in TOON format (AXI §1)."""
    prefix = "  " * indent
    for key, value in data.items():
        if isinstance(value, dict):
            print(f"{prefix}{key}:")
            toon_print_dict(value, indent + 1)
        elif isinstance(value, list):
            if value:
                print(f"{prefix}{key}[{len(value)}]:")
                for item in value:
                    if isinstance(item, dict):
                        toon_print_dict(item, indent + 1)
                    else:
                        print(f"{prefix}  {item}")
            else:
                print(f"{prefix}{key}: 0")
        else:
            print(f"{prefix}{key}: {value}")


def toon_print_array(data: list, schema: str, count: int | None = None) -> None:
    """Print array in TOON format with schema (AXI §1, §2, §4)."""
    if not data:
        print(f"{schema}: 0")
        return
    
    if count is not None:
        print(f"count: {len(data)} of {count} total")
    
    print(f"{schema}[{len(data)}]:")
    for item in data:
        if isinstance(item, dict):
            # Convert dict to comma-separated values
            values = []
            for key in item.keys():
                values.append(str(item[key]))
            print(f"  {','.join(values)}")
        else:
            print(f"  {item}")


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
        import tomllib

        pyproject_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "pyproject.toml"
        )
        with open(pyproject_path, "rb") as f:
            data = tomllib.load(f)
            return data["project"]["version"]
    except Exception:
        return "unknown"


# ── Tool registry ──────────────────────────────────────────────────────────

TOOLS = [
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


# ── AXI §8: Content-first home view ───────────────────────────────────────

def show_home_view() -> None:
    """Show live state when no args provided (AXI §8)."""
    bin_path = _get_bin_path()
    version = get_version()
    profile_dir = get_profile_dir()
    
    has_session = False
    source_state = None
    try:
        source_state = load_source_state(profile_dir)
        has_session = source_state is not None and profile_exists(profile_dir)
    except Exception as e:
        # Log warning but don't fail — session check is best-effort
        print(f"warning: Session check failed: {e}", file=sys.stderr)

    # AXI §10: Tool identity header
    print(f"bin: {bin_path}")
    print(f"version: {version}")
    print("description: Instagram MCP server — profiles, posts, reels, stories, DMs, and account actions")
    print()

    # Live session state
    print("session:")
    if has_session and source_state:
        print("  status: valid")
        print(f"  runtime_id: {get_runtime_id()}")
        print(f"  source_runtime: {source_state.source_runtime_id}")
    else:
        print("  status: not_configured")
        print("  help: Run `instagram-httpx-mcp --login` to create a session")
    print()

    # Tool listing in TOON format (AXI §2: minimal schema)
    tools_data = [{"name": name, "description": desc} for name, desc in TOOLS]
    toon_print_array(tools_data, "tools")
    print()

    # AXI §9: Contextual disclosure
    print("help[4]:")
    print("  Run `instagram-httpx-mcp --tool-info <name>` for detailed parameters")
    print("  Run `instagram-httpx-mcp --list-tools` to see all tools")
    print("  Run `instagram-httpx-mcp --login` to import browser cookies")
    print("  Run `instagram-httpx-mcp` to start the MCP server")


def list_tools_and_exit() -> None:
    """List all available MCP tools and exit (AXI §8 content-first)."""
    tools_data = [{"name": name, "description": desc} for name, desc in TOOLS]
    toon_print_array(tools_data, "tools", count=len(TOOLS))
    print()
    print("help[2]:")
    print("  Run `instagram-httpx-mcp --tool-info <name>` for details")
    print("  Run `instagram-httpx-mcp` to start the MCP server")
    sys.exit(0)


def tool_info_and_exit(tool_name: str) -> None:
    """Show detailed info for a specific tool (AXI §9 contextual disclosure)."""
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
        toon_print_dict(tools_info[tool_name])
    else:
        valid = list(tools_info.keys())
        axi_error(f"Unknown tool: '{tool_name}'", f"Valid tools: {', '.join(valid)}")
    sys.exit(0)


# ── AXI §7: Session integrations ─────────────────────────────────────────────

def install_session_hook_and_exit() -> None:
    """Install session hooks for Claude Code/Codex (AXI §7)."""
    import json
    from pathlib import Path
    
    bin_path = _get_bin_path()
    home_dir = Path.home()
    
    # Try Claude Code hooks
    claude_settings = home_dir / ".claude" / "settings.json"
    try:
        if claude_settings.exists():
            with open(claude_settings, "r") as f:
                settings = json.load(f)
            
            # Add SessionStart hook
            if "hooks" not in settings:
                settings["hooks"] = {}
            
            # Install instagram-httpx-mcp session hook
            hook_command = f"{bin_path}" if bin_path.startswith("~") else sys.argv[0]
            settings["hooks"]["SessionStart"] = hook_command
            
            with open(claude_settings, "w") as f:
                json.dump(settings, f, indent=2)
            
            print("status: success")
            print("target: claude_code")
            print(f"hook: SessionStart -> {hook_command}")
            print("help: Session will now show Instagram MCP state on startup")
        else:
            print("warning: Claude Code settings not found")
            print("help: Install Claude Code to enable session hooks")
    except Exception as e:
        print(f"error: Failed to install Claude Code hook: {e}")
        sys.exit(1)
    
    # Try Codex hooks
    codex_hooks = home_dir / ".codex" / "hooks.json"
    try:
        if codex_hooks.exists():
            with open(codex_hooks, "r") as f:
                hooks = json.load(f)
            
            # Add SessionStart hook
            hook_command = f"{bin_path}" if bin_path.startswith("~") else sys.argv[0]
            hooks["SessionStart"] = hook_command
            
            with open(codex_hooks, "w") as f:
                json.dump(hooks, f, indent=2)
            
            print("status: success")
            print("target: codex")
            print(f"hook: SessionStart -> {hook_command}")
        else:
            print("warning: Codex hooks not found")
            print("help: Install Codex to enable session hooks")
    except Exception as e:
        print(f"error: Failed to install Codex hook: {e}")
        sys.exit(1)
    
    sys.exit(0)


def install_agent_skill_and_exit() -> None:
    """Create installable agent skill from home view (AXI §7)."""
    from pathlib import Path
    
    skill_dir = Path.home() / ".claude" / "skills" / "instagram-mcp"
    skill_dir.mkdir(parents=True, exist_ok=True)
    
    skill_content = """name: Instagram MCP Server
description: Instagram automation with smart aspect ratio processing, modern specs support, and multi-account management
triggers:
  - "instagram post"
  - "instagram upload"
  - "instagram reels"
  - "instagram stories"
  - "instagram dm"
  - "instagram automation"
  - "social media posting"
  - "content creation"

## Overview
Instagram MCP Server provides intelligent Instagram content creation with:
- Smart aspect ratio detection and conversion (4:5, 1:1, 1.91:1, 9:16)
- Extended video durations (180s feed/reels, 60s stories)
- Multi-account support with posting limits
- Advanced media processing with letterbox/crop modes
- DM automation and trigger system

## Quick Start
```bash
# Show home view with live state
instagram-httpx-mcp

# Import browser cookies
instagram-httpx-mcp --login

# Check session status
instagram-httpx-mcp --status

# List available tools
instagram-httpx-mcp --list-tools

# Start MCP server
instagram-httpx-mcp
```

## MCP Tools
- `ias_get_user_profile` - Get user profile information
- `ias_get_user_stories` - Get user stories
- `ias_get_user_highlights` - Get story highlights
- `ias_get_media_feed` - Get user media feed
- `ias_get_media_detail` - Get detailed post information
- `ias_get_media_comments` - Get post comments
- `ias_get_user_reels` - Get user reels
- `ias_search_users` - Search Instagram users
- `ias_get_followers` - Get user followers
- `ias_get_following` - Get user following
- `ias_send_direct_message` - Send DM to user
- `ias_get_direct_messages` - Get DM threads
- `ias_create_post_container` - Create media container
- `ias_publish_media` - Publish media to feed
- `ias_like_media` - Like a post
- `ias_comment_on_media` - Comment on post

## Smart Processing
- **Auto mode**: Media-type-aware processing (fit for stories/reels, crop for feed)
- **Fit mode**: Letterbox/pillarbox preserves entire content
- **Crop mode**: Center crop for full-bleed aesthetic
- **Aspect ratios**: 4:5 (feed standard), 1:1 (square), 1.91:1 (landscape), 9:16 (stories/reels)

## Session Integration
Install session hooks for ambient context:
```bash
instagram-httpx-mcp --install-hook
```

This shows Instagram session state on every agent session start.
"""
    
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text(skill_content)
    
    print("status: success")
    print(f"skill_path: {skill_file}")
    print("help: Agent skill installed - will load automatically on Instagram-related tasks")
    sys.exit(0)


# ── Profile management helpers ─────────────────────────────────────────────

def clear_profile_and_exit() -> None:
    """Clear Instagram profile and exit (AXI §6 idempotent mutations)."""
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
        print("status: nothing_to_clear")
        print("message: No authentication state found")
        sys.exit(0)

    if clear_auth_state(profile_dir):
        print("status: success")
        print("message: Authentication state cleared")
    else:
        print("error: Failed to clear authentication state")
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
        print("error: No valid source session")
        print(f"profile_dir: {profile_dir}")
        print("help: Run with --login to create a source session")
        sys.exit(1)

    print(f"profile_dir: {profile_dir}")
    print(f"runtime_id: {get_runtime_id()}")
    if source_state:
        print(f"source_runtime: {source_state.source_runtime_id}")
        print(f"login_generation: {source_state.login_generation}")

    valid = asyncio.run(_check_session_api())

    if valid:
        print("status: valid")
        sys.exit(0)

    print("status: expired")
    print("help: Run with --login to re-authenticate")
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


# ── Help output ────────────────────────────────────────────────────────────

def show_help() -> None:
    """Show usage information (AXI §10)."""
    version = get_version()
    print(f"instagram-httpx-mcp v{version}")
    print("Instagram MCP server — profiles, posts, reels, stories, DMs, and account actions")
    print()
    print("Usage:")
    print("  instagram-httpx-mcp                    Show home view with live state")
    print("  instagram-httpx-mcp --list-tools       List all available MCP tools")
    print("  instagram-httpx-mcp --tool-info <name> Show details for a specific tool")
    print("  instagram-httpx-mcp --login            Import cookies from browser")
    print("  instagram-httpx-mcp --logout           Clear stored session")
    print("  instagram-httpx-mcp --status           Check authentication status")
    print("  instagram-httpx-mcp --install-hook     Install session hooks (Claude Code/Codex)")
    print("  instagram-httpx-mcp --install-skill    Install agent skill for auto-discovery")
    print("  instagram-httpx-mcp --help             Show this help message")
    print()
    print("Session Integration:")
    print("  --install-hook    Install session hooks for ambient context")
    print("  --install-skill   Install agent skill for task-based discovery")
    print()
    print("Examples:")
    print("  instagram-httpx-mcp --tool-info ias_get_user_profile")
    print("  instagram-httpx-mcp --list-tools")
    print("  instagram-httpx-mcp --login")
    print("  instagram-httpx-mcp --install-hook")


# ── Graceful shutdown ──────────────────────────────────────────────────────

def exit_gracefully(exit_code: int = 0) -> None:
    try:
        asyncio.run(close_browser())
    except Exception:
        pass
    sys.exit(exit_code)


# ── Main entry point ───────────────────────────────────────────────────────

def main() -> None:
    """Main application entry point."""
    config = get_config()

    configure_logging(
        log_level=config.server.log_level,
        json_format=not config.is_interactive and config.server.log_level != "DEBUG",
    )

    # Parse sys.argv directly for AXI-compliant flag handling
    # (We use config.server for flags that need config, but raw args for AXI)
    raw_args = sys.argv[1:]

    # AXI §6: No interactive prompts — validate all flags before proceeding
    if "--help" in raw_args or "-h" in raw_args:
        show_help()
        sys.exit(0)

    if "--list-tools" in raw_args:
        list_tools_and_exit()

    if "--tool-info" in raw_args:
        idx = raw_args.index("--tool-info")
        if idx + 1 >= len(raw_args):
            axi_error("--tool-info requires a tool name", "Usage: instagram-httpx-mcp --tool-info <tool-name>")
        tool_info_and_exit(raw_args[idx + 1])

    # AXI §7: Session integrations
    if "--install-hook" in raw_args:
        install_session_hook_and_exit()

    if "--install-skill" in raw_args:
        install_agent_skill_and_exit()

    # Note: argparse handles unknown flag validation (exit code 2)
    # This satisfies AXI §6 requirement for failing loud on unrecognized input

    if config.server.logout:
        clear_profile_and_exit()

    if config.server.login:
        get_profile_and_exit()

    if config.server.status:
        profile_info_and_exit()

    # No args: show content-first home view (AXI §8)
    if len(raw_args) == 0:
        show_home_view()
        sys.exit(0)

    # Start MCP server
    try:
        transport = config.server.transport

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
        print(f"error: Server runtime error: {e}")
        exit_gracefully(1)
    finally:
        teardown_trace_logging(keep_traces=False)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        exit_gracefully(0)
    except Exception as e:
        print(f"error: Error running MCP server: {e}")
        exit_gracefully(1)