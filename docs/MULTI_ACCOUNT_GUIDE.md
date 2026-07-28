# Multi-Account Management Guide

## Overview

The Instagram MCP Server now supports managing multiple Instagram accounts with separate sessions and cookies. This is designed for AI agents that need to operate on behalf of multiple Instagram accounts during scheduled workflows.

## Architecture

- **Account Storage**: Each account has its own profile directory under `~/.instagram-mcp/accounts/`
- **Cookie Management**: Separate cookie files per account for independent authentication
- **Active Account**: One account is designated as "active" for operations that don't specify an account
- **Account Metadata**: Tracks username, account ID, creation date, last used timestamp, and active status

## Account Management Tools

### List Instagram Accounts

```python
# List all configured accounts
result = await mcp.call_tool("list_instagram_accounts", {})
```

Returns:
```json
{
  "accounts": [
    {
      "account_id": "username_abc123",
      "username": "my_username",
      "full_name": "My Full Name",
      "profile_pic_url": "https://...",
      "is_active": true,
      "created_at": "2026-07-29T00:00:00Z",
      "last_used": "2026-07-29T12:00:00Z"
    }
  ],
  "total_accounts": 2,
  "active_account": "username_abc123"
}
```

### Add Instagram Account

```python
# Add account with cookies
result = await mcp.call_tool("add_instagram_account", {
  "username": "my_username",
  "cookies": {
    "sessionid": "your_session_id",
    "csrftoken": "your_csrftoken",
    "ds_user_id": "your_user_id"
  },
  "full_name": "My Full Name",
  "profile_pic_url": "https://...",
  "set_as_active": true
})
```

### Import Account from Browser

```python
# Import directly from browser cookies
result = await mcp.call_tool("import_account_from_browser", {
  "username": "my_username",
  "browser": "chrome",
  "set_as_active": true
})
```

Supported browsers: `chrome`, `firefox`, `brave`, `edge`, `safari`, `zen`, `librewolf`, `waterfox`, `helium`, `chromium`, `opera`, `vivaldi`, `arc`, `floorp`

### Switch Active Account

```python
# Switch to a different account
result = await mcp.call_tool("switch_active_account", {
  "account_id": "username_abc123"
})
```

### Get Active Account

```python
# Get current active account info
result = await mcp.call_tool("get_active_account_info", {})
```

### Remove Instagram Account

```python
# Remove an account configuration
result = await mcp.call_tool("remove_instagram_account", {
  "account_id": "username_abc123"
})
```

### Update Account Cookies

```python
# Refresh cookies for an account
result = await mcp.call_tool("update_account_cookies", {
  "account_id": "username_abc123",
  "cookies": {
    "sessionid": "new_session_id",
    "csrftoken": "new_csrftoken"
  }
})
```

## Using Account-Specific Operations

Most tools now support an optional `account_id` parameter:

```python
# Use specific account for operations
result = await mcp.call_tool("get_user_profile", {
  "username": "natgeo",
  "account_id": "business_account_abc123"
})

# Use active account (default)
result = await mcp.call_tool("get_user_profile", {
  "username": "natgeo"
})
```

Tools that support account selection:
- `get_user_profile`
- `get_user_posts`
- `get_user_reels`
- `get_user_stories`
- `get_direct_inbox`
- `get_dm_conversation`
- `send_dm`
- `follow_user`
- `unfollow_user`
- `like_post`
- `unlike_post`
- `save_post`
- `comment_on_post`
- `get_home_feed`
- `get_discover_feed`
- `get_user_timeline`

## Account Storage Structure

```
~/.instagram-mcp/
├── accounts/
│   ├── username_abc123/
│   │   ├── account-metadata.json
│   │   └── cookies.json
│   ├── business_account_xyz/
│   │   ├── account-metadata.json
│   │   └── cookies.json
│   └── triggers/
│       ├── triggers-config.json
│       └── executions/
│           ├── trigger_abc123.jsonl
│           └── trigger_xyz456.jsonl
```

## AI Agent Workflow

### Typical Multi-Account Workflow

1. **Initial Setup**: Import all required accounts
```python
accounts = [
  {"username": "personal_account", "browser": "chrome"},
  {"username": "business_account", "browser": "firefox"},
  {"username": "agency_account", "browser": "brave"}
]

for acc in accounts:
  await mcp.call_tool("import_account_from_browser", acc)
```

2. **Switch Context**: Use different accounts for different tasks
```python
# Personal browsing
await mcp.call_tool("switch_active_account", {"account_id": "personal_account_abc"})
await mcp.call_tool("get_home_feed", {"max_posts": 20})

# Business operations
await mcp.call_tool("switch_active_account", {"account_id": "business_account_xyz"})
await mcp.call_tool("get_business_insights", {})
```

3. **Account-Specific Operations**: Specify account directly
```python
# Check DMs on business account while personal is active
await mcp.call_tool("get_direct_inbox", {
  "account_id": "business_account_xyz",
  "limit": 10
})
```

## Troubleshooting

### Account Not Found
- Ensure the account ID is correct
- Check that the account was properly created
- Verify the account directory exists under `~/.instagram-mcp/accounts/`

### Cookie Issues
- Cookies may expire periodically
- Use `update_account_cookies` to refresh
- Re-import from browser if needed
- Check that required cookies (`sessionid`, `csrftoken`) are present

### Active Account Confusion
- Use `get_active_account_info` to verify current active account
- Explicitly specify `account_id` when you need certainty
- Use `switch_active_account` to change context

## Security Considerations

- Account directories are created with restricted permissions (chmod 600)
- Cookie files contain sensitive authentication data
- Protect the `~/.instagram-mcp/` directory from unauthorized access
- Regularly rotate session cookies for security
- Don't commit account directories to version control