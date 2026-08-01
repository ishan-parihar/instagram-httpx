"""
Tool registry for direct CLI execution.

This module is separate from cli_main to avoid circular imports when
early-intercepting tool names in __main__.py.
"""

import asyncio
import json
import os
import sys
from typing import Any

# Mock Context for direct CLI execution
class MockContext:
    """Mock FastMCP Context for direct CLI tool execution."""
    
    def __init__(self):
        self._progress = []
    
    async def report_progress(self, message: str, progress: float = 0.0, total: float = 100.0):
        """Mock progress reporting."""
        self._progress.append((message, progress, total))
        # Optionally print progress to stdout
        if progress > 0:
            print(f"Progress: {progress:.0%}/{total:.0%} - {message}")

TOOLS = [
    # User
    ("get_user_profile", "Get user profile"),
    ("get_user_posts", "Get user posts"),
    ("get_user_reels", "Get user reels"),
    ("get_user_stories", "Get user stories"),
    ("get_user_highlights", "Get user highlights"),
    ("get_user_timeline", "Get user timeline"),
    ("get_user_followers", "Get user followers"),
    ("get_user_following", "Get user following"),
    ("search_users", "Search users"),
    ("follow_user", "Follow user"),
    ("unfollow_user", "Unfollow user"),
    # Feed
    ("get_home_feed", "Get home feed"),
    ("get_discover_feed", "Get discover feed"),
    # Posts
    ("get_post_details", "Get post details"),
    ("like_post", "Like post"),
    ("unlike_post", "Unlike post"),
    ("comment_on_post", "Comment on post"),
    ("save_post", "Save post"),
    # Hashtag/Location
    ("get_hashtag_posts", "Get hashtag posts"),
    ("get_location_posts", "Get location posts"),
    ("search_locations", "Search locations"),
    # Messaging
    ("get_direct_inbox", "Get direct inbox"),
    ("get_dm_conversation", "Get DM conversation"),
    ("send_dm", "Send direct message"),
    # Posting
    ("upload_photo", "Upload photo"),
    ("upload_video", "Upload video"),
    ("upload_reel", "Upload reel"),
    ("upload_carousel", "Upload carousel"),
    ("upload_story", "Upload story"),
    # Account Management
    ("add_instagram_account", "Add Instagram account"),
    ("list_instagram_accounts", "List Instagram accounts"),
    ("remove_instagram_account", "Remove Instagram account"),
    ("get_active_account_info", "Get active account info"),
    ("switch_active_account", "Switch active account"),
    ("update_account_cookies", "Update account cookies"),
    ("import_account_from_browser", "Import account from browser"),
    # DM Triggers
    ("create_dm_trigger", "Create DM trigger"),
    ("list_dm_triggers", "List DM triggers"),
    ("get_dm_trigger", "Get DM trigger"),
    ("update_dm_trigger", "Update DM trigger"),
    ("delete_dm_trigger", "Delete DM trigger"),
    ("pause_dm_trigger", "Pause DM trigger"),
    ("resume_dm_trigger", "Resume DM trigger"),
    ("execute_trigger_dm", "Execute trigger DM"),
    ("check_comment_for_triggers", "Check comment for triggers"),
    ("get_trigger_executions_log", "Get trigger executions log"),
    # Session
    ("close_session", "Close browser session"),
]


def axi_error(primary: str, detail: str) -> None:
    """AXI §6: Error output (fail loud)."""
    print(f"error: {primary}")
    print(f"help: {detail}")
    sys.exit(1)


def toon_print_dict(data: Any, indent: int = 0) -> None:
    """TOON (Tree-Oriented Object Notation) output for dicts."""
    indent_str = "  " * indent
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, dict):
                print(f"{indent_str}{key}:")
                toon_print_dict(value, indent + 1)
            elif isinstance(value, list):
                print(f"{indent_str}{key}:")
                for item in value:
                    if isinstance(item, dict):
                        toon_print_dict(item, indent + 1)
                    else:
                        print(f"{indent_str}  - {item}")
            else:
                print(f"{indent_str}{key}: {value}")
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                toon_print_dict(item, indent)
            else:
                print(f"{indent_str}- {item}")
    else:
        print(f"{indent_str}{data}")


def run_tool_direct(tool_name: str, args: list[str], use_json: bool = False) -> None:
    """Execute a tool directly from CLI without MCP protocol."""
    
    # Set environment variable to prevent argparse from processing tool args
    os.environ["INSTAGRAM_MCP_TOOL_MODE"] = "1"
    
    # Temporarily override sys.argv to prevent argparse from processing tool args
    original_argv = sys.argv
    sys.argv = [sys.argv[0]]  # Keep only the script name
    
    try:
        # Lazy import to avoid argparse conflicts during early interception
        from instagram_mcp_server.server import create_mcp_server
    finally:
        sys.argv = original_argv
        # Keep INSTAGRAM_MCP_TOOL_MODE set during tool execution

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

    # Handle tools with no required parameters
    if not required_params and positional:
        axi_error(
            f"Unexpected positional arg: '{positional[0]}'",
            f"Tool `{tool_name}` takes no positional arguments",
        )

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

    # Prepare context for direct CLI execution
    ctx = MockContext()
    kwargs["ctx"] = ctx

    # Call the tool
    try:
        result = asyncio.run(tool.fn(**kwargs))
    except SystemExit:
        raise
    except TypeError as e:
        # Catch missing required args (e.g. "missing 1 required positional argument")
        error_msg = str(e)
        if "missing" in error_msg and "required" in error_msg:
            axi_error(
                f"Tool `{tool_name}` requires additional parameters",
                f"Run `instagram-httpx --tool-info {tool_name}` to see parameters.",
            )
        else:
            axi_error(f"Tool `{tool_name}` failed: {e}", "Check your configuration and try again")
    except Exception as e:
        axi_error(f"Tool `{tool_name}` failed: {e}", "Check your configuration and try again")

    # Output
    if use_json:
        print(json.dumps(result, indent=2))
    else:
        # AXI §1: TOON is default
        toon_print_dict(result)