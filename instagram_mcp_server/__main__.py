#!/usr/bin/env python3
"""Entry point for instagram-mcp-server command."""

import sys
import os

# ── Direct tool invocation: instagram-httpx-mcp <tool_name> [args...] ──────
# Intercept BEFORE any imports to avoid argparse conflicts
if len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
    # Set environment variable early before any imports
    os.environ["INSTAGRAM_MCP_TOOL_MODE"] = "1"
    
    # Import only what we need for early interception (tool_registry has minimal imports)
    from instagram_mcp_server.tool_registry import TOOLS, axi_error, run_tool_direct
    
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

def main() -> None:
    """Main entry point that delegates to cli_main."""
    from instagram_mcp_server.cli_main import main as cli_main
    cli_main()

if __name__ == "__main__":
    main()
