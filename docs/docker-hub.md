# Instagram MCP Server

A Model Context Protocol (MCP) server that connects AI assistants to Instagram. Access profiles, posts, insights, search, messaging, and account actions through a Docker container.

## Features

- **Profile Access**: Get detailed Instagram user profile information (bio, followers, following, post count)
- **Posts & Reels**: Retrieve user posts and reels with engagement metrics
- **Stories & Highlights**: Read active stories and story highlights
- **Search**: Search users and locations by keyword
- **Hashtag & Location Posts**: Fetch posts by hashtag or tagged location
- **Direct Messages**: Read inbox and conversations, send DMs
- **Account Actions**: Follow, unfollow, like, unlike, save, comment
- **Compact References**: Return typed per-section links alongside readable text without shipping full-page markdown
- **Reel Transcription**: Download and transcribe reels (requires optional `caption` CLI)
- **Reel Analysis**: Multimodal analysis with Gemini (`analyze_reel_with_gemini`)

## Quick Start

Create a browser profile locally, then mount it into Docker. You still need [uv](https://docs.astral.sh/uv/getting-started/installation/) installed on the host for the one-time `uvx instagram-lyr --login` step. Docker already includes its own Chromium runtime, so the managed Patchright Chromium browser download used by MCPB/`uvx` is not needed here.

**Step 1: Create profile on the host (one-time setup)**

```bash
uvx instagram-lyr --login
```

This opens a browser window where you log in manually (5 minute timeout for 2FA, captcha, etc.). The browser profile and cookies are saved under `~/.instagram-mcp/`. On startup, Docker derives a Linux browser profile from your host cookies and creates a fresh session each time.

**Step 2: Configure Claude Desktop with Docker**

```json
{
  "mcpServers": {
    "instagram": {
      "command": "docker",
      "args": [
        "run", "--rm", "-i",
        "-v", "~/.instagram-mcp:/home/pwuser/.instagram-mcp",
        "ishan-parihar/instagram-lyr:latest"
      ]
    }
  }
}
```

> **Note:** Docker containers don't have a display server, so you can't use the `--login` command in Docker. Create a source profile on your host first.
>
> **Note:** `stdio` is the default transport. Add `--transport streamable-http` only when you specifically want HTTP mode.
>
> **Note:** Tool calls are serialized within one server process to protect the
shared Instagram browser session. Concurrent client requests queue instead of
running in parallel. Use `LOG_LEVEL=DEBUG` to see scraper lock logs.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `USER_DATA_DIR` | `~/.instagram-mcp/profile` | Path to persistent browser profile directory |
| `LOG_LEVEL` | `WARNING` | Logging level: DEBUG, INFO, WARNING, ERROR |
| `TIMEOUT` | `5000` | Browser timeout in milliseconds |
| `USER_AGENT` | - | Custom browser user agent |
| `TRANSPORT` | `stdio` | Transport mode: stdio, streamable-http |
| `HOST` | `127.0.0.1` | HTTP server host (for streamable-http transport) |
| `PORT` | `8000` | HTTP server port (for streamable-http transport) |
| `HTTP_PATH` | `/mcp` | HTTP server path (for streamable-http transport) |
| `SLOW_MO` | `0` | Delay between browser actions in ms (debugging) |
| `VIEWPORT` | `1280x720` | Browser viewport size as WIDTHxHEIGHT |
| `CHROME_PATH` | - | Path to Chrome/Chromium executable (rarely needed in Docker) |
| `INSTAGRAM_TRACE_MODE` | `on_error` | Trace/log retention mode: `on_error` keeps ephemeral artifacts only when a failure occurs, `always` keeps every run, `off` disables trace persistence |

**Example with custom timeout:**

```json
{
  "mcpServers": {
    "instagram": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "-v", "~/.instagram-mcp:/home/pwuser/.instagram-mcp",
        "-e", "TIMEOUT=10000",
        "ishan-parihar/instagram-lyr"
      ]
    }
  }
}
```

## Repository

- **Source**: <https://github.com/ishan-parihar/instagram-lyr>
- **License**: MIT
