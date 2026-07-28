# Multi-Account Integration Plan for Media Posting

## Current Multi-Account System Overview

The existing multi-account system provides:

- **Account Storage**: `~/.instagram-mcp/accounts/[account_id]/`
- **Cookie Management**: Account-specific cookies in `cookies.json`
- **Metadata Storage**: Account details in `account-metadata.json`
- **Active Account Management**: Track and switch active accounts
- **Browser Import**: Import cookies from various browsers

### Existing Key Functions

```python
# From multi_account.py
- create_account(username, cookies, full_name, profile_pic_url, set_as_active)
- get_account(account_id)
- get_active_account()
- list_accounts()
- switch_active_account(account_id)
- remove_account(account_id)
- update_account_cookies(account_id, cookies)
- get_account_cookies(account_id)
- update_account_last_used(account_id)
```

## Integration Strategy

### 1. Posting Client Integration

The `PostingClient` class will use the existing multi-account system:

```python
class PostingClient:
    """Wrapper around instagrapi with multi-account support."""
    
    def __init__(self, account_id: str | None = None):
        self.account_id = account_id
        self.cookies = self._get_cookies()
        self.client = self._create_client()
    
    def _get_cookies(self) -> dict:
        """Get cookies for account (with fallback to active account)."""
        if self.account_id:
            cookies = get_account_cookies(self.account_id)
            if not cookies:
                raise AuthenticationError(f"Account {self.account_id} not found")
            return cookies
        else:
            active = get_active_account()
            if not active:
                raise AuthenticationError("No active account")
            cookies = get_account_cookies(active.account_id)
            if not cookies:
                raise AuthenticationError("No cookies for active account")
            return cookies
    
    def _create_client(self) -> Client:
        """Create instagrapi client with account cookies."""
        client = Client()
        client.set_cookies(self.cookies)
        return client
```

### 2. Account Selection in Tools

All posting tools will follow the existing pattern:

```python
async def upload_photo(
    image_path: str,
    caption: str,
    account_id: str | None = None,  # Optional account selection
    ctx: Context = CurrentContext(),
) -> dict[str, Any]:
    # Tool implementation
    client = await get_ready_posting_client(ctx, tool_name="upload_photo", account_id=account_id)
    # ... rest of implementation
```

### 3. Dependency Integration

Update `dependencies.py` to include posting client:

```python
async def get_ready_posting_client(
    ctx: Context | None,
    *,
    tool_name: str,
    account_id: str | None = None,
) -> PostingClient:
    """Get a posting client for media upload operations.
    
    Args:
        ctx: MCP context
        tool_name: Name of the tool being executed
        account_id: Optional account ID to use for cookie loading
    
    Returns:
        Authenticated PostingClient instance
    """
    try:
        from instagram_mcp_server.posting.client import PostingClient
        
        await ensure_tool_ready_or_raise(tool_name, ctx)
        client = PostingClient(account_id=account_id)
        return client
    except AuthenticationError as e:
        await handle_auth_error(e, ctx)
    except Exception as e:
        raise_tool_error(e, tool_name)
```

## Account-Specific Features

### 1. Account Posting Preferences

Add posting-specific metadata to accounts:

```python
@dataclass
class AccountMetadata:
    """Metadata for an Instagram account."""
    account_id: str
    username: str
    full_name: str | None = None
    profile_pic_url: str | None = None
    created_at: str | None = None
    last_used: str | None = None
    is_active: bool = True
    
    # NEW: Posting-specific fields
    posting_enabled: bool = True
    daily_post_limit: int = 10
    last_post_time: str | None = None
    post_count_today: int = 0
    last_reset_date: str | None = None
```

### 2. Account Posting History

Add posting history tracking:

```python
def get_account_posting_history(account_id: str, limit: int = 50) -> list[dict]:
    """Get posting history for an account."""
    history_file = account_dir(account_id) / "posting-history.jsonl"
    
    if not history_file.exists():
        return []
    
    history = []
    with open(history_file) as f:
        for line in f.readlines()[-limit:]:
            history.append(json.loads(line))
    
    return history

def record_post_attempt(
    account_id: str,
    media_type: str,
    success: bool,
    post_id: str | None = None,
    error_message: str | None = None
):
    """Record a post attempt in account history."""
    history_file = account_dir(account_id) / "posting-history.jsonl"
    
    entry = {
        "timestamp": utcnow_iso(),
        "media_type": media_type,
        "success": success,
        "post_id": post_id,
        "error_message": error_message
    }
    
    with open(history_file, "a") as f:
        f.write(json.dumps(entry) + "\n")
    
    # Update account metadata
    if success:
        update_account_last_used(account_id)
        _increment_account_post_count(account_id)
```

### 3. Account-Level Rate Limiting

Implement account-specific rate limiting:

```python
def check_account_posting_limits(account_id: str) -> tuple[bool, str]:
    """Check if account has reached posting limits."""
    account = get_account(account_id)
    if not account:
        return False, "Account not found"
    
    if not account.posting_enabled:
        return False, "Posting disabled for this account"
    
    # Check daily limit
    if account.daily_post_limit > 0:
        if account.post_count_today >= account.daily_post_limit:
            return False, f"Daily posting limit reached ({account.post_count_today}/{account.daily_post_limit})"
    
    # Check cooldown
    if account.last_post_time:
        from datetime import datetime, timedelta
        last_post = datetime.fromisoformat(account.last_post_time)
        cooldown = timedelta(minutes=30)  # 30-minute cooldown
        if datetime.now() - last_post < cooldown:
            remaining = cooldown - (datetime.now() - last_post)
            return False, f"Account in cooldown ({remaining.seconds//60} minutes remaining)"
    
    return True, ""

def _increment_account_post_count(account_id: str):
    """Increment daily post count for account."""
    account = get_account(account_id)
    if not account:
        return
    
    from datetime import datetime
    
    # Reset count if new day
    if account.last_reset_date:
        last_reset = datetime.fromisoformat(account.last_reset_date)
        if last_reset.date() < datetime.now().date():
            account.post_count_today = 0
            account.last_reset_date = datetime.now().isoformat()
    
    account.post_count_today += 1
    account.last_post_time = datetime.now().isoformat()
    
    # Save updated metadata
    save_account_metadata(account)
```

## Account Rotation Strategy

### 1. Automatic Account Selection

Implement intelligent account selection for posting:

```python
def select_best_account_for_posting(media_type: str = "photo") -> AccountMetadata | None:
    """Select the best account for posting based on limits and history."""
    accounts = list_accounts()
    
    # Filter to accounts with posting enabled
    available_accounts = [acc for acc in accounts if acc.posting_enabled]
    
    if not available_accounts:
        return None
    
    # Sort by posting priority (least used first)
    sorted_accounts = sorted(
        available_accounts,
        key=lambda acc: (acc.post_count_today, acc.last_post_time or "")
    )
    
    # Check each account for limits
    for account in sorted_accounts:
        can_post, reason = check_account_posting_limits(account.account_id)
        if can_post:
            return account
    
    return None  # No account available for posting
```

### 2. Account Pool Management

```python
class AccountPool:
    """Manage pool of accounts for posting operations."""
    
    def __init__(self):
        self.accounts = list_accounts()
        self.rotation_index = 0
    
    def get_next_account(self) -> AccountMetadata | None:
        """Get next account in rotation."""
        available_accounts = [acc for acc in self.accounts if acc.posting_enabled]
        
        if not available_accounts:
            return None
        
        # Round-robin selection
        account = available_accounts[self.rotation_index % len(available_accounts)]
        self.rotation_index += 1
        
        # Check if account can post
        can_post, reason = check_account_posting_limits(account.account_id)
        if can_post:
            return account
        
        # Try next account
        return self.get_next_account()
    
    def get_account_by_criteria(self, criteria: dict) -> AccountMetadata | None:
        """Get account matching specific criteria."""
        accounts = list_accounts()
        
        filtered = accounts
        if "username" in criteria:
            filtered = [acc for acc in filtered if acc.username == criteria["username"]]
        if "posting_enabled" in criteria:
            filtered = [acc for acc in filtered if acc.posting_enabled == criteria["posting_enabled"]]
        if "min_daily_limit" in criteria:
            filtered = [acc for acc in filtered if acc.daily_post_limit >= criteria["min_daily_limit"]]
        
        return filtered[0] if filtered else None
```

## Session Management Integration

### 1. Session Validation

Add session validation before posting:

```python
def validate_account_session(account_id: str) -> tuple[bool, str]:
    """Validate that account session is active and valid."""
    cookies = get_account_cookies(account_id)
    if not cookies:
        return False, "No cookies found for account"
    
    # Validate sessionid
    if "sessionid" not in cookies:
        return False, "Session ID missing from cookies"
    
    # Try to validate session with instagrapi
    try:
        from instagrapi import Client
        client = Client()
        client.set_cookies(cookies)
        
        # Simple validation - try to get user info
        user_info = client.user_info_by_username_v1(client.username_from_context)
        if user_info:
            return True, "Session valid"
    except Exception as e:
        return False, f"Session validation failed: {str(e)}"
    
    return False, "Unknown validation error"
```

### 2. Session Refresh Logic

```python
def refresh_account_session(account_id: str) -> tuple[bool, str]:
    """Attempt to refresh account session."""
    account = get_account(account_id)
    if not account:
        return False, "Account not found"
    
    # Try to refresh using existing cookies
    try:
        from instagrapi import Client
        client = Client()
        client.set_cookies(get_account_cookies(account_id))
        
        # Attempt a simple API call to refresh session
        client.user_info_by_username_v1(account.username)
        
        # Update cookies if refreshed
        new_cookies = client.get_cookies()
        update_account_cookies(account_id, new_cookies)
        
        return True, "Session refreshed successfully"
    except Exception as e:
        return False, f"Session refresh failed: {str(e)}"
```

## Error Handling and Fallback

### 1. Account Fallback Strategy

```python
def post_with_fallback(
    media_path: str,
    caption: str,
    media_type: str = "photo",
    preferred_account_id: str | None = None
) -> dict[str, Any]:
    """Attempt to post with fallback to other accounts."""
    
    # Try preferred account first
    if preferred_account_id:
        try:
            result = _post_with_account(media_path, caption, media_type, preferred_account_id)
            if result["success"]:
                return result
        except Exception as e:
            logger.warning(f"Failed to post with preferred account {preferred_account_id}: {e}")
    
    # Try other accounts
    account_pool = AccountPool()
    for _ in range(len(account_pool.accounts)):
        account = account_pool.get_next_account()
        if account and account.account_id != preferred_account_id:
            try:
                result = _post_with_account(media_path, caption, media_type, account.account_id)
                if result["success"]:
                    return result
            except Exception as e:
                logger.warning(f"Failed to post with account {account.account_id}: {e}")
    
    return {
        "success": False,
        "error": "All accounts failed to post",
        "error_type": "fallback_exhausted"
    }
```

### 2. Account Health Monitoring

```python
def check_account_health(account_id: str) -> dict[str, Any]:
    """Check health status of an account."""
    account = get_account(account_id)
    if not account:
        return {"healthy": False, "error": "Account not found"}
    
    health_checks = {
        "cookies_valid": False,
        "session_valid": False,
        "posting_enabled": account.posting_enabled,
        "within_limits": False,
        "last_post_time": account.last_post_time,
        "post_count_today": account.post_count_today,
    }
    
    # Check cookies
    cookies = get_account_cookies(account_id)
    health_checks["cookies_valid"] = bool(cookies and "sessionid" in cookies)
    
    # Check session
    if health_checks["cookies_valid"]:
        session_valid, _ = validate_account_session(account_id)
        health_checks["session_valid"] = session_valid
    
    # Check limits
    can_post, _ = check_account_posting_limits(account_id)
    health_checks["within_limits"] = can_post
    
    overall_health = all([
        health_checks["cookies_valid"],
        health_checks["session_valid"],
        health_checks["posting_enabled"],
        health_checks["within_limits"]
    ])
    
    return {
        "healthy": overall_health,
        "account_id": account_id,
        "username": account.username,
        "checks": health_checks
    }
```

## Integration with Existing Features

### 1. DM Automation Integration

```python
# Extend trigger system to support posting
@dataclass
class DMTrigger:
    """Configuration for an automated DM trigger."""
    # ... existing fields ...
    
    # NEW: Auto-posting capabilities
    auto_post_enabled: bool = False
    auto_post_template_id: str | None = None
    auto_post_media_path: str | None = None
    auto_post_caption_template: str | None = None

def execute_trigger_with_posting(trigger: DMTrigger, comment_data: dict) -> dict[str, Any]:
    """Execute trigger with optional auto-posting."""
    result = {
        "dm_sent": False,
        "post_created": False,
        "errors": []
    }
    
    # Send DM
    try:
        dm_result = execute_trigger_dm(trigger.trigger_id, comment_data["username"], ...)
        result["dm_sent"] = dm_result["success"]
    except Exception as e:
        result["errors"].append(f"DM failed: {str(e)}")
    
    # Auto-post if enabled
    if trigger.auto_post_enabled and trigger.auto_post_media_path:
        try:
            caption = trigger.auto_post_caption_template.format(**comment_data)
            post_result = await upload_photo(
                image_path=trigger.auto_post_media_path,
                caption=caption,
                account_id=trigger.account_id
            )
            result["post_created"] = post_result["success"]
        except Exception as e:
            result["errors"].append(f"Auto-post failed: {str(e)}")
    
    return result
```

### 2. Feed Analysis Integration

```python
# Analyze feed and auto-post related content
async def analyze_and_post_trending_content(account_id: str | None = None) -> dict[str, Any]:
    """Analyze feed trends and auto-post related content."""
    account_pool = AccountPool()
    account = account_pool.get_account_by_criteria({"posting_enabled": True})
    
    if not account:
        return {"success": False, "error": "No available account for posting"}
    
    # Get feed data
    feed_data = await get_home_feed(max_posts=50, account_id=account.account_id)
    
    # Analyze trends
    trending_topics = analyze_feed_trends(feed_data)
    
    # Generate content based on trends
    for topic in trending_topics:
        if topic["engagement_score"] > threshold:
            content = generate_content_for_topic(topic)
            
            # Post the content
            post_result = await upload_photo(
                image_path=content["media_path"],
                caption=content["caption"],
                account_id=account.account_id
            )
            
            if post_result["success"]:
                return {
                    "success": True,
                    "posted_topic": topic,
                    "post_result": post_result
                }
    
    return {"success": False, "error": "No trending content posted"}
```

## Configuration and Settings

### 1. Account-Level Configuration

Add posting configuration to account metadata:

```python
@dataclass
class AccountMetadata:
    """Metadata for an Instagram account."""
    # ... existing fields ...
    
    # NEW: Posting configuration
    posting_config: dict[str, Any] = field(default_factory=dict)
    
    # Default posting config
    def __post_init__(self):
        if not self.posting_config:
            self.posting_config = {
                "default_hashtags": [],
                "default_location": None,
                "auto_share_facebook": False,
                "auto_share_threads": False,
                "preferred_media_type": "photo",
                "thumbnail_quality": "high",
                "video_compression": "medium",
            }
```

### 2. Global Posting Settings

Add global posting configuration:

```python
# ~/.instagram-mcp/posting-config.json
{
    "global_defaults": {
        "daily_post_limit": 10,
        "min_post_interval_minutes": 30,
        "max_retries": 3,
        "retry_backoff_minutes": 5,
        "auto_session_refresh": true,
        "fallback_account_enabled": true
    },
    "media_processing": {
        "image_quality": 85,
        "max_image_size": 1080,
        "video_bitrate": "2M",
        "video_codec": "libx264",
        "audio_codec": "aac"
    },
    "rate_limiting": {
        "enable_account_rotation": true,
        "account_cooldown_minutes": 30,
        "global_rate_limit_per_hour": 20
    }
}
```

## Testing Strategy

### 1. Multi-Account Testing

```python
def test_multi_account_posting():
    """Test posting with multiple accounts."""
    accounts = list_accounts()
    
    # Test posting with each account
    for account in accounts:
        if account.posting_enabled:
            client = PostingClient(account_id=account.account_id)
            # Test with dummy media
            result = client.upload_photo("test.jpg", "Test caption")
            assert result["success"]
    
    # Test account fallback
    result = post_with_fallback("test.jpg", "Test caption")
    assert result["success"]
```

### 2. Account Limit Testing

```python
def test_account_limits():
    """Test account posting limits."""
    account = get_active_account()
    
    # Set low limit for testing
    account.daily_post_limit = 2
    account.post_count_today = 2
    
    # Should fail due to limit
    can_post, reason = check_account_posting_limits(account.account_id)
    assert not can_post
    assert "limit reached" in reason.lower()
```

## Conclusion

The multi-account integration for media posting leverages the existing account management system while adding posting-specific features like:

- **Account-specific posting limits and preferences**
- **Intelligent account selection and rotation**
- **Session validation and refresh**
- **Health monitoring and fallback strategies**
- **Integration with existing DM automation and feed analysis**

This ensures that the posting capabilities work seamlessly with the current multi-account architecture while providing robust account management for automated workflows.