# Instagram HTTPX MCP Server

<p align="left">
  <a href="https://pypi.org/project/instagram-lyr/" target="_blank"><img src="https://img.shields.io/pypi/v/instagram-lyr?color=blue" alt="PyPI Version"></a>
  <a href="https://github.com/ishan-parihar/instagram-lyr/actions/workflows/ci.yml" target="_blank"><img src="https://github.com/ishan-parihar/instagram-lyr/actions/workflows/ci.yml/badge.svg?branch=main" alt="CI Status"></a>
  <a href="https://github.com/ishan-parihar/instagram-lyr/actions/workflows/release.yml" target="_blank"><img src="https://github.com/ishan-parihar/instagram-lyr/actions/workflows/release.yml/badge.svg?branch=main" alt="Release"></a>
  <a href="https://github.com/ishan-parihar/instagram-lyr/blob/main/LICENSE" target="_blank"><img src="https://img.shields.io/badge/License-MIT-%233fb950?labelColor=32383f" alt="License"></a>
  <img src="https://img.shields.io/badge/Python-3.12+-blue" alt="Python Version">
</p>

**Model Context Protocol server that lets AI assistants interact with Instagram through intelligent automation.**

Access profiles, posts, reels, Business/Creator insights, direct messages, and full-scope content creation with smart aspect ratio processing, modern Instagram specifications, multi-account management, and agent-optimized CLI interface.

## Quick Install

**One-line installation:**
```bash
curl -fsSL https://raw.githubusercontent.com/ishan-parihar/instagram-lyr/main/install.sh | bash
```

## What It Does

- **Smart Content Processing**: Automatic aspect ratio detection and conversion (4:5, 1:1, 1.91:1, 9:16) with letterbox/crop modes
- **Modern Instagram Specs**: Extended video durations (180s feed/reels, 60s stories) and latest format support
- **Multi-Account Management**: Switch between multiple Instagram accounts with posting limits and cooldowns
- **Comment-Based DM Automation**: Trigger system for automated responses to post comments
- **Feed Browsing**: Home feed, discover feed, and user timeline access
- **Full Content Creation**: Photos, videos, carousels, stories, and reels with location/tagging
- **Agent-Optimized CLI**: AXI-compliant interface with TOON output and session integrations
- **Production Ready**: Systemd persistence, error handling, and comprehensive validation

## Quick Start

**1. Install**

```bash
curl -fsSL https://raw.githubusercontent.com/ishan-parihar/instagram-lyr/main/install.sh | bash
```

**2. Configure your MCP client**

Add to your client's MCP config:

```json
{
  "mcpServers": {
    "instagram": {
      "command": "uvx",
      "args": ["instagram-lyr"]
    }
  }
}
```

**3. First tool call**

Restart your MCP client. On the first Instagram tool call, a login window opens if no session exists. Log in once, and cookies persist across restarts.

## Smart Processing

The server automatically handles Instagram's complex media specifications:

- **Auto Aspect Ratio Detection**: Converts any media to the closest valid Instagram ratio
- **Media-Type-Aware Processing**: Uses letterbox for stories/reels (preserves content), crop for feed (clean aesthetic)
- **Extended Duration Support**: 180s for feed/reels, 60s for stories (vs old 60s/15s limits)
- **Landscape Format Support**: 1.91:1 cinematic format for feed posts
- **Flexible Processing Modes**: Auto, fit (letterbox), and crop (center crop) options

**Example:**
```python
# Auto-detect best ratio and processing mode
result = await upload_photo(
    image_path="photo.jpg",
    caption="Smart processed",
    aspect_ratio="auto",  # Auto-detect closest valid ratio
    fit_mode="auto",  # Auto-select best processing mode
)
```

## AI Agent Setup

AI coding agents in headless environments can authenticate by providing Instagram session cookies directly.

### Option A: Set `INSTAGRAM_COOKIES` environment variable (recommended)

```json
{
  "sessionid": "your_session_id_value",
  "csrftoken": "your_csrf_token_value"
}
```

**Linux/macOS:**
```bash
export INSTAGRAM_COOKIES='{"sessionid":"your_session_id_value","csrftoken":"your_csrf_token_value"}'
uvx instagram-lyr
```

**Windows (PowerShell):**
```powershell
$env:INSTAGRAM_COOKIES='{"sessionid":"your_session_id_value","csrftoken":"your_csrf_token_value"}'
uvx instagram-lyr
```

### Option B: Pass cookies via file

```bash
uvx instagram-lyr --cookies-file /path/to/cookies.json
```

### How to get cookies

1. Open Instagram in a browser and log in
2. Use browser DevTools (`F12` → Application → Cookies → instagram.com)
3. Export cookies as JSON (required: `sessionid`, `csrftoken`)
4. Pass to server via env var or file

> **Note:** Instagram session cookies expire periodically. Refresh cookies when tools return session expired errors.

## CLI Interface (AXI-Compliant)

The CLI provides agent-optimized interaction with TOON output and session integrations:

```bash
# Show home view with live state
instagram-lyr

# List available tools
instagram-lyr --list-tools

# Tool details
instagram-lyr --tool-info ias_get_user_profile

# Session management
instagram-lyr --login
instagram-lyr --status
instagram-lyr --logout

# Agent integrations
instagram-lyr --install-hook    # Session hooks for Claude Code/Codex
instagram-lyr --install-skill   # Agent skill for auto-discovery
```

**Session Integration:**
```bash
$ instagram-lyr --install-hook
status: success
target: claude_code
hook: SessionStart -> ~/instagram-lyr/instagram_mcp_server/__main__.py
help: Session will now show Instagram MCP state on startup
```

## How It Works

The server uses a hybrid approach:

- **Scraping**: Fast httpx-based web scraping for reading content via Instagram's internal API
- **Posting**: instagrapi library for robust media uploads via Instagram's private API
- **Smart Processing**: Automatic aspect ratio detection and media optimization
- **Multi-Account**: Centralized account management with separate sessions and posting limits
- **Validation**: Comprehensive input validation and Instagram spec compliance
- **Error Handling**: Instagram-specific error detection and user-friendly messages

## MCP Client Configuration

### Claude Desktop

```json
{
  "mcpServers": {
    "instagram": {
      "command": "uvx",
      "args": ["instagram-lyr"]
    }
  }
}
```

### Cursor

```json
{
  "mcpServers": {
    "instagram": {
      "command": "uvx",
      "args": ["instagram-lyr"]
    }
  }
}
```

### Windsurf

```json
{
  "mcpServers": {
    "instagram": {
      "command": "uvx",
      "args": ["instagram-lyr"]
    }
  }
}
```

### Generic MCP Client

```json
{
  "mcpServers": {
    "instagram": {
      "command": "uv",
      "args": ["run", "-m", "instagram_mcp_server"]
    }
  }
}
```

## Tools

### Multi-Account Management
| Tool | Description |
|------|-------------|
| `list_instagram_accounts` | List all configured Instagram accounts |
| `add_instagram_account` | Add a new Instagram account with session cookies |
| `import_account_from_browser` | Import Instagram account cookies directly from browser |
| `switch_active_account` | Switch the active Instagram account for operations |
| `get_active_account_info` | Get information about the currently active account |
| `remove_instagram_account` | Remove an Instagram account configuration |
| `update_account_cookies` | Update cookies for an existing Instagram account |

### Feed Browsing
| Tool | Description |
|------|-------------|
| `get_home_feed` | Get the home feed (posts from followed accounts) |
| `get_discover_feed` | Get the discover/explore feed with trending content |
| `get_user_timeline` | Get recent posts from a specific user's timeline |

### Comment-Based DM Automation
| Tool | Description |
|------|-------------|
| `create_dm_trigger` | Create an automated DM trigger for post comments |
| `list_dm_triggers` | List DM triggers with optional filtering |
| `get_dm_trigger` | Get details of a specific DM trigger |
| `update_dm_trigger` | Update an existing DM trigger |
| `pause_dm_trigger` | Pause a DM trigger (temporarily disable) |
| `resume_dm_trigger` | Resume a paused DM trigger |
| `delete_dm_trigger` | Delete a DM trigger |
| `check_comment_for_triggers` | Check if a comment matches any active triggers |
| `execute_trigger_dm` | Execute the DM action for a matched trigger |
| `get_trigger_executions_log` | Get execution history for a specific trigger |

### Content Posting (Smart Processing)
| Tool | Description |
|------|-------------|
| `upload_photo` | Upload photo with smart aspect ratio processing (4:5, 1:1, 1.91:1) |
| `upload_video` | Upload video with smart processing (180s duration, auto aspect ratio) |
| `upload_carousel` | Upload carousel (2-10 images) with consistent smart processing |
| `upload_story` | Upload story with letterbox processing (60s duration, 9:16 format) |
| `upload_reel` | Upload reel with smart vertical processing (180s duration, 9:16 format) |

**Smart Processing Parameters:**
- `aspect_ratio`: "auto", "4:5", "1:1", "1.91:1" (feed), "9:16" (stories/reels)
- `fit_mode`: "auto" (media-type-aware), "fit" (letterbox), "crop" (center crop)
- `max_duration`: Custom duration limits (up to 180s feed/reels, 60s stories)

### Profile & Content
| Tool | Description |
|------|-------------|
| `get_user_profile` | Get profile info with optional sections (posts, reels, stories, highlights, followers, following) |
| `get_user_posts` | Get structured post data (ID, shortcode, URL, thumbnail, media type, caption, engagement) |
| `get_user_reels` | Get reels with engagement metrics (plays, likes, comments) and audio metadata |
| `get_user_stories` | Get active stories with media URLs, viewer counts, and expiry timestamps |
| `get_user_highlights` | Get story highlights with titles, cover URLs, and highlight IDs |
| `get_post_details` | Get detailed post/reel info including caption, engagement, audio, location, and carousel children |

### Search & Discovery
| Tool | Description |
|------|-------------|
| `search_users` | Search for users by name or keywords |
| `search_hashtags` | Search for hashtags by keywords |
| `search_locations` | Search for Instagram locations |
| `get_hashtag_posts` | Get posts for a given hashtag |
| `get_location_posts` | Get posts tagged at a specific location |

### Messaging & Actions
| Tool | Description |
|------|-------------|
| `get_direct_inbox` | List recent DM conversations |
| `get_dm_conversation` | Read a specific DM conversation |
| `send_dm` | Send a direct message to a user |
| `follow_user` | Follow a user (sends follow request for private accounts) |
| `unfollow_user` | Unfollow a user |
| `like_post` | Like a post or reel |
| `unlike_post` | Unlike a post or reel |
| `save_post` | Save a post or reel to a collection |
| `comment_on_post` | Post a comment on a post or reel |

### Business/Creator Insights
| Tool | Description |
|------|-------------|
| `get_account_insights` | Get account-level insights (impressions, reach, engagement, growth) |
| `get_content_insights` | Get insights for specific posts/reels (impressions, reach, engagement) |
| `get_stories_insights` | Get insights for stories (impressions, reach, navigation) |
| `get_audience_insights` | Get audience demographics (age, gender, location, activity) |

### Utility Tools
| Tool | Description |
|------|-------------|
| `close_session` | Close the current Instagram browser session and clean up resources |

## Content Posting Features

### Smart Aspect Ratio Processing
- **Auto Detection**: Automatically finds closest valid Instagram ratio for any input
- **Media-Type-Aware**: Stories/reels use letterbox (preserve content), feed uses crop (clean aesthetic)
- **Flexible Modes**: Auto, fit (letterbox/pillarbox), crop (center crop) options
- **Instagram Ratios**: 4:5 (feed standard), 1:1 (square), 1.91:1 (landscape), 9:16 (stories/reels)

### Extended Video Support
- **Feed/Reels**: Up to 180 seconds (vs old 60s limit)
- **Stories**: Up to 60 seconds (vs old 15s limit)
- **Auto Processing**: Smart aspect ratio conversion and thumbnail generation
- **Quality Preservation**: Optimized compression while maintaining quality

### Advanced Posting Features
- **Multi-Account Support**: Specify `account_id` to post from any configured account
- **Location Tagging**: Add Instagram location IDs to posts
- **User Tagging**: Tag users in posts and stories
- **Cross-Posting**: Share to Facebook and Threads automatically
- **Scheduling**: Schedule posts for future times (ISO 8601 timestamps)
- **Posting Limits**: Built-in daily limits and cooldowns to prevent account restrictions
- **History Tracking**: All posting attempts logged for audit and analysis

### Posting Limitations
- All posting operations require valid Instagram session cookies
- Daily posting limits enforced (default: 10 posts per account per day)
- 30-minute cooldown between posts to prevent rate limiting
- Media files automatically processed to meet Instagram specifications
- Stories have stricter duration limits (60s vs 180s for feed videos)

### Known Issues
- **Two separate cookie stores.** Posting + DMs use a **multi-account store** (`~/.instagram-lyr/accounts/<name>/cookies.json`); follow/like/comment tools gate on a **legacy default profile** (`~/.instagram-lyr/profile/`). On installs without the legacy profile dir present, posting works but every follow/like/comment tool reports "session expired" even with valid cookies — a deployment gap, not a poisoned session.
- **Rate limiting:** Instagram rate-limits test accounts (`PhotoNotUpload`, DM throttling); the tool surfaces this cleanly rather than crashing.
- Runs the browser-based scraping **extractor** (chromedriver, separate auth from the posting client) for profile/feed reads.

## Authentication

| Scenario | What happens |
|----------|-------------|
| **First run** | Cookie extraction window opens. Complete sign-in (including 2FA if needed). Session saved. |
| **Subsequent runs** | Cookies loaded from `~/.instagram-mcp/profile/` automatically. |
| **Session expired** | Re-run `uvx instagram-lyr --login` to re-authenticate. |
| **Clear session** | Run `uvx instagram-lyr --logout` to remove stored cookies. |

> Instagram may request login confirmation on your mobile app for new sessions. If you encounter a captcha, use `--login` to solve it manually in the opened browser.

## Development

```bash
# Install dependencies
uv sync

# Run linting
uv run ruff check .
uv run ruff format .

# Type checking
uv run ty check

# Run tests
uv run pytest

# Run server locally
uv run -m instagram_mcp_server --no-headless

# Install browser for cookie extraction
uv run patchright install chromium
```

## Architecture

The server uses a hybrid approach:
- **Scraping**: Fast httpx-based web scraping for reading content
- **Posting**: instagrapi library for robust media uploads via Instagram's private API
- **Smart Processing**: Automatic aspect ratio detection and media optimization
- **Multi-Account**: Centralized account management with separate sessions
- **Validation**: Comprehensive input validation and media processing
- **Error Handling**: Instagram-specific error detection and user-friendly messages
- **AXI Compliance**: Agent-optimized CLI with TOON output and session integrations

## Production Readiness

This server is production-ready for:
- Multi-account AI agent workflows
- Automated content scheduling and posting
- Comment-based DM automation
- Feed analysis and trend detection
- Business/Creator insight collection
- Systemd persistence and deployment

For systemd persistence and production deployment, see the production documentation in the `docs/` directory.

## Related CLI Tools

This project is part of a family of agent-friendly CLI tools for social platforms:

| Tool | CLI | Repo |
|------|-----|------|
| Instagram | `instagram-lyr` | [ishan-parihar/instagram-lyr](https://github.com/ishan-parihar/instagram-lyr) |
| Reddit | `reddit-lyr` | [ishan-parihar/reddit-lyr](https://github.com/ishan-parihar/reddit-lyr) |
| LinkedIn | `linkedin-lyr` | [ishan-parihar/linkedin-lyr](https://github.com/ishan-parihar/linkedin-lyr) |
| Twitter/X | `twitter-lyr` | [ishan-parihar/twitter-lyr](https://github.com/ishan-parihar/twitter-lyr) |
| Discord | `discord` | [ishan-parihar/discord-cli](https://github.com/ishan-parihar/discord-cli) |
| Telegram | `tg` | [ishan-parihar/tg-cli](https://github.com/ishan-parihar/tg-cli) |

## License

MIT
