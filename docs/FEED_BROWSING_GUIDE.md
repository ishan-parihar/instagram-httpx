# Feed Browsing Guide

## Overview

The Instagram MCP Server now provides tools for browsing Instagram feeds, enabling AI agents to discover content from followed accounts, explore trending content, and access timeline posts programmatically.

## Feed Tools

### Get Home Feed

Browse posts from accounts you follow:

```python
result = await mcp.call_tool("get_home_feed", {
  "max_posts": 50,
  "account_id": "my_account_abc123"  # Optional
})
```

Returns:
```json
{
  "url": "https://www.instagram.com/",
  "sections": {
    "home_feed": "Found 25 posts from your feed"
  },
  "posts": [
    {
      "id": "123456789",
      "shortcode": "Cxyz123",
      "url": "https://www.instagram.com/p/Cxyz123/",
      "thumbnail_url": "https://...",
      "media_type": 1,
      "caption": "Post caption text...",
      "likes_count": 1234,
      "comments_count": 56,
      "timestamp": "2026-07-29T12:00:00Z",
      "username": "username",
      "user_full_name": "Full Name",
      "user_profile_pic": "https://...",
      "is_video": false,
      "video_url": "",
      "play_count": 0,
      "carousel_media": []
    }
  ],
  "total_posts": 25
}
```

### Get Discover Feed

Browse trending and suggested content:

```python
result = await mcp.call_tool("get_discover_feed", {
  "max_posts": 50,
  "account_id": "my_account_abc123"  # Optional
})
```

Returns similar structure to home feed with discover/explore content.

### Get User Timeline

Get recent posts from a specific user:

```python
result = await mcp.call_tool("get_user_timeline", {
  "username": "natgeo",
  "max_posts": 50,
  "account_id": "my_account_abc123"  # Optional
})
```

## Media Types

- `media_type: 1` - Image
- `media_type: 2` - Video
- `media_type: 8` - Carousel (multiple media)

## Post Structure

Each post includes:
- **Basic Info**: ID, shortcode, URL, thumbnail
- **Engagement**: Likes count, comments count
- **Content**: Caption, timestamp
- **User**: Username, full name, profile picture
- **Video**: Video URL, play count (if video)
- **Carousel**: Array of carousel media items (if carousel)

## AI Agent Use Cases

### Content Monitoring

```python
# Monitor home feed for specific keywords
feed = await mcp.call_tool("get_home_feed", {"max_posts": 100})

for post in feed["posts"]:
    if "important" in post.get("caption", "").lower():
        # Flag important content
        await process_important_post(post)
```

### Competitor Analysis

```python
# Monitor competitor activity
competitors = ["competitor1", "competitor2", "competitor3"]

for competitor in competitors:
    timeline = await mcp.call_tool("get_user_timeline", {
      "username": competitor,
      "max_posts": 20
    })
    await analyze_competitor_posts(timeline["posts"])
```

### Trending Content Discovery

```python
# Discover trending content
discover = await mcp.call_tool("get_discover_feed", {"max_posts": 50})

for post in discover["posts"]:
    if post["likes_count"] > 10000:
        # Identify high-performing content
        await analyze_viral_content(post)
```

### Scheduled Feed Checks

```python
# Cron job to check feed periodically
async def scheduled_feed_check():
    feed = await mcp.call_tool("get_home_feed", {"max_posts": 20})
    
    for post in feed["posts"]:
        # Check for engagement spikes
        if post["likes_count"] > previous_average * 2:
            await notify_engagement_spike(post)
```

## Account Selection

All feed tools support optional `account_id` parameter:

```python
# Use specific account
feed = await mcp.call_tool("get_home_feed", {
  "max_posts": 50,
  "account_id": "business_account_abc"
})

# Use active account (default)
feed = await mcp.call_tool("get_home_feed", {"max_posts": 50})
```

## Limitations

- Feed browsing requires an authenticated account
- Some content may be restricted based on privacy settings
- Rate limits apply to feed fetching
- Historic feed access is limited to recent posts

## Best Practices

- **Cache Results**: Store feed data locally to avoid repeated API calls
- **Rate Limiting**: Implement delays between feed requests
- **Error Handling**: Handle empty feeds gracefully
- **Account Rotation**: Use different accounts for different feed types
- **Selective Fetching**: Only fetch needed post data (limit max_posts)

## Performance Tips

- Use smaller `max_posts` values for real-time monitoring
- Batch multiple feed operations together
- Process feed data asynchronously
- Use `account_id` to avoid unnecessary account switching
