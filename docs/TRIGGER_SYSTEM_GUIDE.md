# Comment-Based DM Automation Guide

## Overview

The Instagram MCP Server now includes a powerful comment-based DM automation system. This allows AI agents to set up automated direct message responses when users comment on specific posts with trigger words or phrases. Perfect for lead generation, customer engagement, and automated follow-ups.

## How It Works

1. **Setup**: Create a DM trigger for a specific post with trigger words
2. **Monitoring**: When someone comments on the post, check if it matches the trigger
3. **Action**: If matched, automatically send a pre-configured DM to the commenter
4. **Analytics**: Track trigger executions and cooldown periods

## Trigger Tools

### Create DM Trigger

```python
result = await mcp.call_tool("create_dm_trigger", {
  "account_id": "business_account_abc",
  "post_shortcode": "Cxyz123",
  "post_url": "https://www.instagram.com/p/Cxyz123/",
  "trigger_words": ["interest", "info", "pricing"],
  "dm_template": "Hi {username}! Thanks for your interest. Here's the info you requested...",
  "match_type": "contains",
  "description": "Lead generation trigger for promotional post",
  "cooldown_minutes": 60,
  "max_triggers_per_user": 1,
  "case_sensitive": false
})
```

Parameters:
- `account_id`: Account to use for sending DMs
- `post_shortcode`: Post shortcode (e.g., "Cxyz123")
- `post_url`: Full post URL
- `trigger_words`: List of words/phrases that trigger the DM
- `dm_template`: Message template (use `{username}` placeholder)
- `match_type`: How to match (`exact`, `contains`, `starts_with`, `ends_with`, `regex`)
- `description`: Optional description for the trigger
- `cooldown_minutes`: Minimum minutes between triggers for same user (0 = no cooldown)
- `max_triggers_per_user`: Maximum times to trigger per user (0 = unlimited)
- `case_sensitive`: Whether matching should be case sensitive

### List DM Triggers

```python
# List all triggers
result = await mcp.call_tool("list_dm_triggers", {})

# Filter by account
result = await mcp.call_tool("list_dm_triggers", {
  "account_id": "business_account_abc"
})

# Filter by post
result = await mcp.call_tool("list_dm_triggers", {
  "post_shortcode": "Cxyz123"
})

# Filter by status
result = await mcp.call_tool("list_dm_triggers", {
  "status": "active"
})
```

### Get DM Trigger Details

```python
result = await mcp.call_tool("get_dm_trigger", {
  "trigger_id": "trigger_abc123"
})
```

### Update DM Trigger

```python
result = await mcp.call_tool("update_dm_trigger", {
  "trigger_id": "trigger_abc123",
  "trigger_words": ["new_interest", "updated_info"],
  "dm_template": "Updated message template...",
  "status": "active"
})
```

### Pause/Resume DM Trigger

```python
# Pause trigger temporarily
result = await mcp.call_tool("pause_dm_trigger", {
  "trigger_id": "trigger_abc123"
})

# Resume paused trigger
result = await mcp.call_tool("resume_dm_trigger", {
  "trigger_id": "trigger_abc123"
})
```

### Delete DM Trigger

```python
result = await mcp.call_tool("delete_dm_trigger", {
  "trigger_id": "trigger_abc123"
})
```

## Comment Monitoring

### Check Comment for Triggers

```python
result = await mcp.call_tool("check_comment_for_triggers", {
  "post_shortcode": "Cxyz123",
  "comment_text": "I'm interested in this product",
  "commenter_username": "potential_customer",
  "comment_id": "comment_abc123"
})
```

Returns:
```json
{
  "matched": true,
  "trigger_id": "trigger_abc123",
  "matched_word": "interested",
  "account_id": "business_account_abc",
  "dm_template": "Hi {username}! Thanks for your interest...",
  "message": "Comment matched trigger trigger_abc123"
}
```

### Execute Trigger DM

```python
result = await mcp.call_tool("execute_trigger_dm", {
  "trigger_id": "trigger_abc123",
  "commenter_username": "potential_customer",
  "comment_id": "comment_abc123",
  "matched_word": "interested",
  "account_id": "business_account_abc"  # Optional override
})
```

Returns:
```json
{
  "success": true,
  "dm_sent": true,
  "dm_message_id": "msg_xyz789",
  "trigger_id": "trigger_abc123",
  "commenter_username": "potential_customer",
  "message": "DM sent successfully"
}
```

### Get Trigger Executions

```python
result = await mcp.call_tool("get_trigger_executions_log", {
  "trigger_id": "trigger_abc123",
  "limit": 100
})
```

## Match Types

- **exact**: Comment must exactly match the trigger word
- **contains**: Comment contains the trigger word (default)
- **starts_with**: Comment starts with the trigger word
- **ends_with**: Comment ends with the trigger word
- **regex**: Regular expression matching

## Complete AI Agent Workflow

### Automated Comment Monitoring

```python
async def monitor_post_comments(post_shortcode):
    """Monitor comments on a post and auto-respond"""
    
    # Get recent comments for the post
    comments = await get_post_comments(post_shortcode)
    
    for comment in comments:
        # Check if comment matches any triggers
        match_result = await mcp.call_tool("check_comment_for_triggers", {
            "post_shortcode": post_shortcode,
            "comment_text": comment["text"],
            "commenter_username": comment["username"],
            "comment_id": comment["id"]
        })
        
        if match_result["matched"]:
            # Execute the DM trigger
            await mcp.call_tool("execute_trigger_dm", {
                "trigger_id": match_result["trigger_id"],
                "commenter_username": comment["username"],
                "comment_id": comment["id"],
                "matched_word": match_result["matched_word"]
            })
```

### Scheduled Trigger Check

```python
async def scheduled_trigger_check():
    """Cron job to check triggers and respond"""
    
    # Get all active triggers
    triggers = await mcp.call_tool("list_dm_triggers", {
        "status": "active"
    })
    
    for trigger in triggers["triggers"]:
        # Monitor comments for each trigger's post
        await monitor_post_comments(trigger["post_shortcode"])
```

### Lead Generation Workflow

```python
async def setup_lead_generation(post_url, trigger_words, message_template):
    """Setup lead generation for a promotional post"""
    
    # Extract shortcode from URL
    shortcode = extract_shortcode(post_url)
    
    # Create trigger
    result = await mcp.call_tool("create_dm_trigger", {
        "account_id": "business_account",
        "post_shortcode": shortcode,
        "post_url": post_url,
        "trigger_words": trigger_words,
        "dm_template": message_template,
        "match_type": "contains",
        "cooldown_minutes": 30,
        "max_triggers_per_user": 2
    })
    
    return result["trigger_id"]
```

## Cooldown and Rate Limiting

### Cooldown Periods

Prevent spamming the same user with multiple DMs:

```python
# Set 1-hour cooldown between triggers
await mcp.call_tool("create_dm_trigger", {
  "cooldown_minutes": 60,
  # ... other parameters
})
```

### Max Triggers Per User

Limit how many times a user can trigger the same response:

```python
# Allow maximum 3 triggers per user
await mcp.call_tool("create_dm_trigger", {
  "max_triggers_per_user": 3,
  # ... other parameters
})
```

## Trigger Analytics

### Monitor Trigger Performance

```python
# Get execution history
executions = await mcp.call_tool("get_trigger_executions_log", {
  "trigger_id": "trigger_abc123",
  "limit": 100
})

# Calculate success rate
sent_count = sum(1 for e in executions["executions"] if e["dm_sent"])
total_count = len(executions["executions"])
success_rate = sent_count / total_count if total_count > 0 else 0
```

### A/B Testing Triggers

```python
# Create two triggers with different templates
trigger_a = await mcp.call_tool("create_dm_trigger", {
  "trigger_words": ["interest"],
  "dm_template": "Template A message...",
  "post_shortcode": "Cxyz123",
  "post_url": "https://www.instagram.com/p/Cxyz123/",
  "account_id": "business_account"
})

trigger_b = await mcp.call_tool("create_dm_trigger", {
  "trigger_words": ["interested"],
  "dm_template": "Template B message...",
  "post_shortcode": "Cxyz123",
  "post_url": "https://www.instagram.com/p/Cxyz123/",
  "account_id": "business_account"
})
```

## Best Practices

### Message Templates

- **Personalization**: Use `{username}` placeholder for personalization
- **Clarity**: Keep messages concise and actionable
- **Value**: Provide actual value, not just fluff
- **Compliance**: Ensure messages comply with Instagram's terms

### Trigger Words

- **Specific**: Use specific words rather than generic ones
- **Relevant**: Choose words related to your offering
- **Variety**: Include synonyms and variations
- **Case**: Consider case sensitivity for better matching

### Rate Limiting

- **Cooldowns**: Always set cooldowns to prevent spam
- **Limits**: Use max_triggers_per_user to avoid over-messaging
- **Monitoring**: Regularly check trigger execution logs
- **Pausing**: Pause triggers during non-business hours

### Account Management

- **Separate Accounts**: Use dedicated business accounts for DM automation
- **Session Refresh**: Regularly update account cookies
- **Multiple Triggers**: Spread triggers across multiple accounts
- **Active Switching**: Switch to appropriate account before execution

## Troubleshooting

### DM Not Sending

1. Check trigger status is "active"
2. Verify account cookies are valid
3. Ensure cooldown period has passed
4. Check max_triggers_per_user limit
5. Review trigger execution logs for errors

### Comment Not Matching

1. Verify match_type is correct
2. Check case sensitivity setting
3. Ensure trigger word is in comment text
4. Test with exact match for debugging
5. Check for whitespace or special characters

### Account Issues

1. Verify account_id is correct
2. Check account has valid cookies
3. Ensure account is not rate-limited
4. Test with `get_active_account_info`
5. Try switching to the account first

## Security Considerations

- **Permission**: Only automate DMs for accounts you own or manage
- **Compliance**: Follow Instagram's terms of service for automated messaging
- **Privacy**: Handle user data responsibly
- **Consent**: Ensure users can opt-out of automated messages
- **Transparency**: Be clear about automated nature in message templates