---
name: instagram-mcp
description: >
  Interact with Instagram via MCP. Access profiles, posts, reels, stories,
  Business/Creator insights, direct messages, and account actions.
---

# Instagram MCP Skill

Interact with Instagram via MCP — profiles, posts, reels, DMs, and analytics.

<!-- Static skill -->
<!-- Install: npx skills add <owner/instagram-lyr> --skill instagram-mcp -->
<!-- CI check: diff <(instagram-lyr --help) SKILL.md && exit 1 -->
<!-- Install: npx skills add <owner/instagram-lyr> --skill instagram-mcp -->

## Quick Start

```bash
# Run the MCP server
instagram-lyr

# Or with uvx
uvx instagram-lyr
```

## MCP Configuration

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

## Key Tools

| Tool | Description |
|------|-------------|
| `get_user_profile` | Get profile info with optional sections |
| `get_user_posts` | Get structured post data |
| `get_user_reels` | Get reels with engagement metrics |
| `get_user_stories` | Get active stories |
| `search_users` | Search for users |
| `search_hashtags` | Search hashtags |
| `send_dm` | Send a direct message |
| `like_post` | Like a post or reel |
| `comment_on_post` | Post a comment |
| `get_business_insights` | Get reach, impressions, engagement |
| `get_audience_insights` | Get audience demographics |
| `get_content_insights` | Get content performance data |
| `transcribe_reel` | Transcribe a reel to SRT |
| `analyze_reel_with_gemini` | AI reel analysis with Gemini |

And more — run the MCP server to see all 28 tools.|

## Authentication

Set `INSTAGRAM_COOKIES` env var or run `--login` for browser-based auth.
