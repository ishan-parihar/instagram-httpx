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
    ("add_instagram_account", "Add Instagram account with cookies"),
    ("check_comment_for_triggers", "Check if comment matches DM triggers"),
    ("close_session", "Close browser session"),
    ("comment_on_post", "Comment on a post"),
    ("create_dm_trigger", "Create DM trigger for automated responses"),
    ("delete_dm_trigger", "Delete DM trigger"),
    ("execute_trigger_dm", "Execute DM trigger manually"),
    ("follow_user", "Follow Instagram user"),
    ("get_active_account_info", "Get active Instagram account info"),
    ("get_direct_inbox", "Get direct message inbox"),
    ("get_discover_feed", "Get discover feed"),
    ("get_dm_conversation", "Get DM conversation"),
    ("get_dm_trigger", "Get DM trigger details"),
    ("get_hashtag_posts", "Get posts from hashtag"),
    ("get_home_feed", "Get home feed"),
    ("get_location_posts", "Get posts from location"),
    ("get_post_details", "Get post details"),
    ("get_trigger_executions_log", "Get DM trigger execution log"),
    ("get_user_highlights", "Get user highlights"),
    ("get_user_posts", "Get user posts"),
    ("get_user_profile", "Get user profile"),
    ("get_user_reels", "Get user reels"),
    ("get_user_stories", "Get user stories"),
    ("get_user_timeline", "Get user timeline"),
    ("import_account_from_browser", "Import Instagram account from browser"),
    ("like_post", "Like post"),
    ("list_dm_triggers", "List DM triggers"),
    ("list_instagram_accounts", "List Instagram accounts"),
    ("pause_dm_trigger", "Pause DM trigger"),
    ("remove_instagram_account", "Remove Instagram account"),
    ("resume_dm_trigger", "Resume DM trigger"),
    ("save_post", "Save post"),
    ("search_locations", "Search locations"),
    ("search_users", "Search users"),
    ("send_dm", "Send direct message"),
    ("switch_active_account", "Switch active Instagram account"),
    ("unfollow_user", "Unfollow user"),
    ("unlike_post", "Unlike post"),
    ("update_account_cookies", "Update account cookies"),
    ("update_dm_trigger", "Update DM trigger"),
    ("upload_carousel", "Upload carousel"),
    ("upload_photo", "Upload photo"),
    ("upload_reel", "Upload reel"),
    ("upload_story", "Upload story"),
    ("upload_video", "Upload video"),
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
    # Simple placeholder - for full implementation, this would need to introspect the actual tools
    tools_info = {
        "get_user_profile": {
            "name": "get_user_profile",
            "description": "Get Instagram user profile information by username",
            "parameters": {"username": "string (required)"},
            "returns": "Profile data including bio, followers, following, and posts",
        },
        "get_user_posts": {
            "name": "get_user_posts",
            "description": "Get user's media feed posts",
            "parameters": {"username": "string (required)", "limit": "number (optional)"},
            "returns": "Array of media objects with id, shortcode, url, thumbnail, media_type",
        },
        "get_user_stories": {
            "name": "get_user_stories",
            "description": "Get user active stories",
            "parameters": {"username": "string (required)"},
            "returns": "Array of story objects with media_url, timestamp, expires_at",
        },
        "search_users": {
            "name": "search_users",
            "description": "Search for Instagram users",
            "parameters": {"query": "string (required)", "limit": "number (optional)"},
            "returns": "Array of user objects with username, full_name, profile_pic_url",
        },
    }
    if tool_name in tools_info:
        toon_print_dict(tools_info[tool_name])
    else:
        valid = list(tools_info.keys())
        axi_error(f"Tool info not available for: '{tool_name}'", f"Available tool info: {', '.join(valid)}")
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
- Direct CLI tool execution without MCP server

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

# Execute tools directly
instagram-httpx-mcp get_user_profile --username natgeo
instagram-httpx-mcp get_user_posts --username natgeo --limit 5

# Start MCP server
instagram-httpx-mcp
```

## Direct CLI Tool Execution
You can call Instagram MCP tools directly from the CLI without starting the MCP server:
```bash
# Get user profile
instagram-httpx-mcp get_user_profile --username natgeo

# Get user posts
instagram-httpx-mcp get_user_posts --username natgeo --limit 10

# Search users
instagram-httpx-mcp search_users --query photography --limit 20

# Get user stories
instagram-httpx-mcp get_user_stories --username natgeo

# Output as JSON
instagram-httpx-mcp get_user_profile --username natgeo --json
```

## MCP Tools
- `get_user_profile` - Get user profile information
- `get_user_posts` - Get user posts
- `get_user_stories` - Get user stories
- `get_user_highlights` - Get user highlights
- `get_user_reels` - Get user reels
- `get_user_timeline` - Get user timeline
- `get_home_feed` - Get home feed
- `get_discover_feed` - Get discover feed
- `get_post_details` - Get post details
- `search_users` - Search Instagram users
- `search_locations` - Search locations
- `get_hashtag_posts` - Get hashtag posts
- `get_location_posts` - Get location posts
- `follow_user` - Follow user
- `unfollow_user` - Unfollow user
- `like_post` - Like post
- `unlike_post` - Unlike post
- `save_post` - Save post
- `comment_on_post` - Comment on post
- `send_dm` - Send direct message
- `get_direct_inbox` - Get direct message inbox
- `get_dm_conversation` - Get DM conversation
- `upload_photo` - Upload photo
- `upload_video` - Upload video
- `upload_reel` - Upload reel
- `upload_story` - Upload story
- `upload_carousel` - Upload carousel
- `list_instagram_accounts` - List Instagram accounts
- `import_account_from_browser` - Import account from browser
- `switch_active_account` - Switch active account

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


def run_tool_direct(tool_name: str, args: list[str], use_json: bool = False) -> None:
    """Execute a tool directly from CLI without MCP protocol."""
    import asyncio
    from instagram_mcp_server.server import create_mcp_server

    # Parse --key value pairs into a dict
    kwargs = {}
    positional = []
    i = 0
    while i < len(args):
        arg = args[i]
        if arg.startswith("--"):
            key = arg[2:]
            if i + 1 < len(args) and not args[i + 1].startswith("--"):
                kwargs[key] = args[i + 1]
                i += 2
            else:
                kwargs[key] = "true"
                i += 1
        else:
            positional.append(arg)
            i += 1

    # Get tool object
    mcp = create_mcp_server()
    tools = asyncio.run(mcp.list_tools())
    tool = next((t for t in tools if t.name == tool_name), None)
    if not tool:
        valid = sorted(t.name for t in tools)
        axi_error(f"Unknown tool: '{tool_name}'", f"Valid tools: {', '.join(valid)}")

    # Map positional args to required params
    schema = tool.parameters or {}
    props = schema.get("properties", {})
    required = schema.get("required", [])
    required_params = [p for p in required if p in props]

    for idx, val in enumerate(positional):
        if idx < len(required_params):
            kwargs[required_params[idx]] = val
        else:
            axi_error(
                f"Unexpected positional arg: '{val}'",
                f"Tool `{tool_name}` expects: {', '.join(required_params)}",
            )

    # Type coercion from schema
    for key, val in list(kwargs.items()):
        if key in props:
            prop = props[key]
            prop_type = prop.get("type", "string")
            try:
                if prop_type == "integer":
                    kwargs[key] = int(val)
                elif prop_type == "number":
                    kwargs[key] = float(val)
                elif prop_type == "boolean":
                    kwargs[key] = val.lower() in ("true", "1", "yes")
            except (ValueError, TypeError):
                axi_error(
                    f"Invalid value for `{key}`: '{val}' (expected {prop_type})",
                    f"Tool `{tool_name}` parameter `{key}` expects type {prop_type}",
                )

    # Call the tool
    try:
        result = asyncio.run(tool.fn(**kwargs))
    except SystemExit:
        raise
    except TypeError as e:
        # Catch missing required args (e.g. "missing 1 required positional argument")
        axi_error(
            f"Tool `{tool_name}` missing required argument",
            f"Run `instagram-httpx --tool-info {tool_name}` to see required parameters",
        )
    except Exception as e:
        axi_error(f"Tool `{tool_name}` failed: {e}")

    # Output
    if use_json:
        print(json.dumps(result, indent=2))
    else:
        # AXI §1: TOON is default
        toon_print_dict(result)


# ── Help output ────────────────────────────────────────────────────────────

def show_help() -> None:
    """Show usage information (AXI §10)."""
    version = get_version()
    print(f"instagram-httpx-mcp v{version}")
    print("Instagram MCP server — profiles, posts, reels, stories, DMs, and account actions")
    print()
    print("Usage:")
    print("  instagram-httpx-mcp                    Show home view with live state")
    print("  instagram-httpx-mcp <tool> [args]      Call a tool directly (see examples)")
    print("  instagram-httpx-mcp --list-tools       List all available MCP tools")
    print("  instagram-httpx-mcp --tool-info <name> Show details for a specific tool")
    print("  instagram-httpx-mcp --login            Import cookies from browser")
    print("  instagram-httpx-mcp --logout           Clear stored session")
    print("  instagram-httpx-mcp --status           Check authentication status")
    print("  instagram-httpx-mcp --install-hook     Install session hooks (Claude Code/Codex)")
    print("  instagram-httpx-mcp --install-skill    Install agent skill for auto-discovery")
    print("  instagram-httpx-mcp --json            Render tool results as JSON (default is TOON)")
    print("  instagram-httpx-mcp --help             Show this help message")
    print()
    print("Session Integration:")
    print("  --install-hook    Install session hooks for ambient context")
    print("  --install-skill   Install agent skill for task-based discovery")
    print()
    print("Examples:")
    print("  instagram-httpx-mcp get_user_profile --username natgeo")
    print("  instagram-httpx-mcp get_user_posts --username natgeo --limit 5")
    print("  instagram-httpx-mcp --tool-info get_user_profile")
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
    # ── Direct tool invocation: instagram-httpx-mcp <tool_name> [args...] ──────
    # Intercept BEFORE any config loading to avoid argparse conflicts
    if len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
        tool_name = sys.argv[1]
        tool_names = [t[0] for t in TOOLS]
        if tool_name in tool_names:
            # Filter out CLI-only flags, keep tool args
            use_json = "--json" in sys.argv
            remaining = [a for a in sys.argv[2:] if a != "--json"]
            run_tool_direct(tool_name, remaining, use_json=use_json)
            sys.exit(0)
        # Looks like a tool name but doesn't match — fail early with valid list
        axi_error(
            f"Unknown tool: '{tool_name}'",
            f"Valid tools: {', '.join(tool_names)}",
        )

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