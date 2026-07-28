# MCP Tools Design for Media Posting

## Tool Design Principles

Following the existing patterns in the instagram-httpx-mcp project:

1. **Consistent Naming**: Use descriptive, action-oriented tool names
2. **Account Selection**: All tools support optional `account_id` parameter
3. **Error Handling**: Use existing error handling patterns
4. **Progress Reporting**: Use MCP context for progress updates
5. **Guard Functions**: Use `@tool_guard` decorator for gating
6. **Destructive Annotations**: Mark write operations with `destructiveHint: True`

## Core Posting Tools

### 1. Upload Photo Tool

```python
@mcp.tool(
    timeout=TOOL_TIMEOUT_SECONDS,
    title="Upload Photo",
    annotations={"destructiveHint": True, "openWorldHint": True},
    tags={"posting", "media", "photo"},
)
@tool_guard("upload_photo")
async def upload_photo(
    image_path: str,
    caption: str,
    account_id: str | None = None,
    location_id: str | None = None,
    user_tags: list[str] | None = None,
    extra_data: dict[str, str] | None = None,
    schedule_at: str | None = None,
    share_to_facebook: bool = False,
    share_to_threads: bool = False,
    ctx: Context = CurrentContext(),
) -> dict[str, Any]:
    """
    Upload a photo to Instagram feed.
    
    Args:
        image_path: Path to image file (JPG/PNG, max 1080px)
        caption: Photo caption (max 2200 characters)
        account_id: Optional account ID to use for the upload
        location_id: Optional Instagram location ID for tagging
        user_tags: Optional list of usernames to tag in the photo
        extra_data: Optional additional metadata for the post
        schedule_at: Optional ISO 8601 timestamp for scheduled posting
        share_to_facebook: Whether to cross-post to Facebook
        share_to_threads: Whether to cross-post to Threads
    
    Returns:
        Dict with upload status, post URL, and media information
    """
    client = await get_ready_posting_client(ctx, tool_name="upload_photo", account_id=account_id)
    
    logger.info(f"Uploading photo: {image_path}")
    await ctx.report_progress("Validating image", 0)
    
    # Validate inputs
    from instagram_mcp_server.posting.validators import PostingValidator
    
    valid, msg = PostingValidator.validate_photo_path(image_path)
    if not valid:
        return {"success": False, "error": msg}
    
    valid, msg = PostingValidator.validate_caption(caption)
    if not valid:
        return {"success": False, "error": msg}
    
    await ctx.report_progress("Processing image", 25)
    
    # Process image if needed
    from instagram_mcp_server.posting.media_processor import MediaProcessor
    
    try:
        processed_path = MediaProcessor.process_image(image_path)
        logger.info(f"Processed image: {processed_path}")
    except Exception as e:
        logger.error(f"Image processing failed: {e}")
        return {"success": False, "error": f"Image processing failed: {str(e)}"}
    
    await ctx.report_progress("Uploading to Instagram", 50)
    
    # Upload using instagrapi
    try:
        media = client.upload_photo(
            path=processed_path,
            caption=caption,
            location=location_id,
            usertags=user_tags,
            extra_data=extra_data or {},
            schedule_at=schedule_at,
            share_to_facebook=share_to_facebook,
            share_to_threads=share_to_threads,
        )
        
        await ctx.report_progress("Complete", 100)
        
        return {
            "success": True,
            "post_id": media.pk,
            "post_shortcode": media.code,
            "post_url": f"https://www.instagram.com/p/{media.code}/",
            "media_type": "photo",
            "taken_at": media.taken_at,
            "caption": caption,
        }
    except Exception as e:
        logger.error(f"Photo upload failed: {e}")
        return {
            "success": False,
            "error": f"Upload failed: {str(e)}",
            "error_type": type(e).__name__
        }
```

### 2. Upload Video Tool

```python
@mcp.tool(
    timeout=TOOL_TIMEOUT_SECONDS,
    title="Upload Video",
    annotations={"destructiveHint": True, "openWorldHint": True},
    tags={"posting", "media", "video"},
)
@tool_guard("upload_video")
async def upload_video(
    video_path: str,
    caption: str,
    account_id: str | None = None,
    thumbnail_path: str | None = None,
    location_id: str | None = None,
    user_tags: list[str] | None = None,
    extra_data: dict[str, str] | None = None,
    schedule_at: str | None = None,
    share_to_facebook: bool = False,
    share_to_threads: bool = False,
    ctx: Context = CurrentContext(),
) -> dict[str, Any]:
    """
    Upload a video to Instagram feed.
    
    Args:
        video_path: Path to video file (MP4, max 60s duration)
        caption: Video caption (max 2200 characters)
        account_id: Optional account ID to use for the upload
        thumbnail_path: Optional path to thumbnail image
        location_id: Optional Instagram location ID for tagging
        user_tags: Optional list of usernames to tag in the video
        total_extra_data: Optional additional metadata for the post
        schedule_at: Optional ISO 8601 timestamp for scheduled posting
        share_to_facebook: Whether to cross-post to Facebook
        share_to_threads: Whether to cross-post to Threads
    
    Returns:
        Dict with upload status, post URL, and media information
    """
    client = await get_ready_posting_client(ctx, tool_name="upload_video", account_id=account_id)
    
    logger.info(f"Uploading video: {video_path}")
    await ctx.report_progress("Validating video", 0)
    
    # Validate inputs
    from instagram_mcp_server.posting.validators import PostingValidator
    
    valid, msg = PostingValidator.validate_video_path(video_path)
    if not valid:
        return {"success": False, "error": msg}
    
    valid, msg = PostingValidator.validate_caption(caption)
    if not valid:
        return {"success": False, "error": msg}
    
    await ctx.report_progress("Processing video", 25)
    
    # Process video if needed
    from instagram_mcp_server.posting.media_processor import MediaProcessor
    
    try:
        processed_video, generated_thumbnail = MediaProcessor.process_video(video_path)
        logger.info(f"Processed video: {processed_video}")
        
        # Use provided thumbnail or generated one
        final_thumbnail = thumbnail_path or generated_thumbnail
    except Exception as e:
        logger.error(f"Video processing failed: {e}")
        return {"success": False, "error": f"Video processing failed: {str(e)}"}
    
    await ctx.report_progress("Uploading to Instagram", 50)
    
    # Upload using instagrapi
    try:
        media = client.upload_video(
            path=processed_video,
            caption=caption,
            thumbnail=final_thumbnail,
            location=location_id,
            usertags=user_tags,
            extra_data=extra_data or {},
            schedule_at=schedule_at,
            share_to_facebook=share_to_facebook,
            share_to_threads=share_to_threads,
        )
        
        await ctx.report_progress("Complete", 100)
        
        return {
            "success": True,
            "post_id": media.pk,
            "post_shortcode": media.code,
            "post_url": f"https://www.instagram.com/p/{media.code}/",
            "media_type": "video",
            "taken_at": media.taken_at,
            "caption": caption,
        }
    except Exception as e:
        logger.error(f"Video upload failed: {e}")
        return {
            "success": False,
            "error": f"Upload failed: {str(e)}",
            "error_type": type(e).__name__
        }
```

### 3. Upload Carousel Tool

```python
@mcp.tool(
    timeout=TOOL_TIMEOUT_SECONDS,
    title="Upload Carousel",
    annotations={"destructiveHint": True, "openWorldHint": True},
    tags={"posting", "media", "carousel"},
)
@tool_guard("upload_carousel")
async def upload_carousel(
    media_paths: list[str],
    caption: str,
    account_id: str | None = None,
    location_id: str | None = None,
    user_tags: list[str] | None = None,
    extra_data: dict[str, str] | None = None,
    schedule_at: str | None = None,
    share_to_facebook: bool = False,
    share_to_threads: bool = False,
    ctx: Context = CurrentContext(),
) -> dict[str, Any]:
    """
    Upload multiple media items as a carousel album.
    
    Args:
        media_paths: List of paths to media files (2-10 items, JPG/MP4)
        caption: Carousel caption (applies to entire carousel)
        account_id: Optional account ID to use for the upload
        location_id: Optional Instagram location ID for tagging
        user_tags: Optional list of usernames to tag in the carousel
        extra_data: Optional additional metadata for the post
        schedule_at: Optional ISO 8601 timestamp for scheduled posting
        share_to_facebook: Whether to cross-post to Facebook
        share_to_threads: Whether to cross-post to Threads
    
    Returns:
        Dict with upload status, post URL, and media information
    """
    client = await get_ready_posting_client(ctx, tool_name="upload_carousel", account_id=account_id)
    
    logger.info(f"Uploading carousel with {len(media_paths)} items")
    await ctx.report_progress("Validating carousel items", 0)
    
    # Validate inputs
    from instagram_mcp_server.posting.validators import PostingValidator
    
    valid, msg = PostingValidator.validate_carousel_paths(media_paths)
    if not valid:
        return {"success": False, "error": msg}
    
    valid, msg = PostingValidator.validate_caption(caption)
    if not valid:
        return {"success": False, "error": msg}
    
    await ctx.report_progress("Processing carousel items", 25)
    
    # Process media items
    from instagram_mcp_server.posting.media_processor import MediaProcessor
    
    processed_paths = []
    for media_path in media_paths:
        try:
            if media_path.lower().endswith(('.jpg', '.jpeg', '.png')):
                processed = MediaProcessor.process_image(media_path)
                processed_paths.append(processed)
            elif media_path.lower().endswith(('.mp4', '.mov', '.avi')):
                processed, _ = MediaProcessor.process_video(media_path)
                processed_paths.append(processed)
            else:
                return {"success": False, "error": f"Unsupported media format: {media_path}"}
        except Exception as e:
            logger.error(f"Failed to process {media_path}: {e}")
            return {"success": False, "error": f"Media processing failed for {media_path}: {str(e)}"}
    
    await ctx.report_progress("Uploading carousel to Instagram", 50)
    
    # Upload carousel using instagrapi
    try:
        media = client.upload_carousel(
            paths=processed_paths,
            caption=caption,
            location=location_id,
            usertags=user_tags,
            extra_data=extra_data or {},
            schedule_at=schedule_at,
            share_to_facebook=share_to_facebook,
            share_to_threads=share_to_threads,
        )
        
        await ctx.report_progress("Complete", 100)
        
        return {
            "success": True,
            "post_id": media.pk,
            "post_shortcode": media.code,
            "post_url": f"https://www.instagram.com/p/{media.code}/",
            "media_type": "carousel",
            "item_count": len(media_paths),
            "taken_at": media.taken_at,
            "caption": caption,
        }
    except Exception as e:
        logger.error(f"Carousel upload failed: {e}")
        return {
            "success": False,
            "error": f"Upload failed: {str(e)}",
            "error_type": type(e).__name__
        }
```

### 4. Upload Story Tool

```python
@mcp.tool(
    timeout=TOOL_TIMEOUT_SECONDS,
    title="Upload Story",
    annotations={"destructiveHint": True, "openWorldHint": True},
    tags={"posting", "media", "story"},
)
@tool_guard("upload_story")
async def upload_story(
    media_path: str,
    account_id: str | None = None,
    caption: str | None = None,
    mentions: list[str] | None = None,
    links: list[str] | None = None,
    hashtags: list[str] | None = None,
    resize_mode: str = "fill",
    ctx: Context = CurrentContext(),
) -> dict[str, Any]:
    """
    Upload media to Instagram story.
    
    Args:
        media_path: Path to media file (JPG/MP4, 9:16 aspect ratio recommended)
        account_id: Optional account ID to use for the upload
        caption: Optional story caption text
        mentions: Optional list of usernames to mention
        links: Optional list of URLs to add as link stickers
        hashtags: Optional list of hashtags to add
        resize_mode: Story sizing mode ("fill" or "fit")
    
    Returns:
        Dict with upload status, story information
    """
    client = await get_ready_posting_client(ctx, tool_name="upload_story", account_id=account_id)
    
    logger.info(f"Uploading story: {media_path}")
    await ctx.report_progress("Validating story media", 0)
    
    # Validate media type
    is_video = media_path.lower().endswith(('.mp4', '.mov', '.avi'))
    
    if is_video:
        valid, msg = PostingValidator.validate_video_path(media_path, is_story=True)
    else:
        valid, msg = PostingValidator.validate_photo_path(media_path)
    
    if not valid:
        return {"success": False, "error": msg}
    
    await ctx.report_progress("Processing story media", 25)
    
    # Process media for story (9:16 aspect ratio)
    from instagram_mcp_server.posting.media_processor import MediaProcessor
    
    try:
        if is_video:
            processed_media, thumbnail = MediaProcessor.process_video(media_path, is_story=True)
        else:
            processed_media = MediaProcessor.process_image(media_path, target_aspect=(9, 16))
            thumbnail = None
        
        logger.info(f"Processed story media: {processed_media}")
    except Exception as e:
        logger.error(f"Story media processing failed: {e}")
        return {"success": False, "error": f"Media processing failed: {str(e)}"}
    
    await ctx.report_progress("Uploading story to Instagram", 50)
    
    # Convert mentions, links, hashtags to instagrapi format
    story_mentions = [{"pk": mention} for mention in (mentions or [])] if mentions else []
    story_links = [{"webUri": link} for link in (links or [])] if links else []
    story_hashtags = [{"tag": tag} for tag in (hashtags or [])] if hashtags else []
    
    # Upload story using instagrapi
    try:
        if is_video:
            story = client.upload_story_video(
                path=processed_media,
                caption=caption or "",
                thumbnail=thumbnail,
                mentions=story_mentions,
                links=story_links,
                hashtags=story_hashtags,
                resize_mode=resize_mode,
            )
        else:
            story = client.upload_story_photo(
                path=processed_media,
                caption=caption or "",
                mentions=story_mentions,
                links=story_links,
                hashtags=story_hashtags,
                resize_mode=resize_mode,
            )
        
        await ctx.report_progress("Complete", 100)
        
        return {
            "success": True,
            "story_id": story.pk,
            "story_url": f"https://www.instagram.com/stories/{story.pk}/",
            "media_type": "story",
            "expires_at": story.expiring_at,
            "caption": caption,
        }
    except Exception as e:
        logger.error(f"Story upload failed: {e}")
        return {
            "success": False,
            "error": f"Upload failed: {str(e)}",
            "error_type": type(e).__name__
        }
```

### 5. Upload Reel Tool

```python
@mcp.tool(
    timeout=TOOL_TIMEOUT_SECONDS,
    title="Upload Reel",
    annotations={"destructiveHint": True, "openWorldHint": True},
    tags={"posting", "media", "reel"},
)
@tool_guard("upload_reel")
async def upload_reel(
    video_path: str,
    caption: str,
    account_id: str | None = None,
    thumbnail_path: str | None = None,
    location_id: str | None = None,
    user_tags: list[str] str | None = None,
    extra_data: dict[str, str] | None = None,
    share_to_facebook: bool = False,
    share_to_threads: bool = False,
    topics: list[str] | None = None,
    show_preview_in_feed: bool = True,
    ctx: Context = CurrentContext(),
) -> dict[str, Any]:
    """
    Upload a reel to Instagram.
    
    Args:
        video_path: Path to video file (MP4, max 60s duration, 9:16 aspect ratio)
        caption: Reel caption (max 2200 characters)
        account_id: Optional account ID to use for the upload
        thumbnail_path: Optional path to thumbnail image
        location_id: Optional Instagram location ID for tagging
        user_tags: Optional list of usernames to tag in the reel
        extra_data: Optional additional metadata for the reel
        share_to_facebook: Whether to cross-post to Facebook
        share_to_threads: Whether to cross-post to Threads
        topics: Optional list of Reel topic IDs for discoverability
        show_preview_in_feed: Whether to show preview in feed
    
    Returns:
        Dict with upload status, reel URL, and media information
    """
    client = await get_ready_posting_client(ctx, tool_name="upload_reel", account_id=account_id)
    
    logger.info(f"Uploading reel: {video_path}")
    await ctx.report_progress("Validating reel media", 0)
    
    # Validate inputs
    from instagram_mcp_server.posting.validators import PostingValidator
    
    valid, msg = PostingValidator.validate_video_path(video_path, is_story=False)
    if not valid:
        return {"success": False, "error": msg}
    
    valid, msg = PostingValidator.validate_caption(caption)
    if not valid:
        return {"success": False, "error": msg}
    
    await ctx.report_progress("Processing reel", 25)
    
    # Process reel media
    from instagram_mcp_server.posting.media_processor import MediaProcessor
    
    try:
        processed_reel, generated_thumbnail = MediaProcessor.process_video(video_path, is_story=False)
        logger.info(f"Processed reel: {processed_reel}")
        
        # Use provided thumbnail or generated one
        final_thumbnail = thumbnail_path or generated_thumbnail
    except Exception as e:
        logger.error(f"Reel processing failed: {e}")
        return {"success": False, "error": f"Reel processing failed: {str(e)}"}
    
    await ctx.report_progress("Uploading reel to Instagram", 50)
    
    # Upload reel using instagrapi
    try:
        media = client.upload_reel(
            path=processed_reel,
            caption=caption,
            thumbnail=final_thumbnail,
            location=location_id,
            usertags=user_tags,
            extra_data=extra_data or {},
            share_to_facebook=share_to_facebook,
            share_to_threads=share_to_threads,
            topics=topics,
            show_preview_in_feed=show_preview_in_feed,
        )
        
        await ctx.report_progress("Complete", 100)
        
        return {
            "success": True,
            "reel_id": media.pk,
            "reel_shortcode": media.code,
            "reel_url": f"https://www.instagram.com/reel/{media.code}/",
            "media_type": "reel",
            "taken_at": media.taken_at,
            "caption": caption,
        }
    except Exception as e:
        logger.error(f"Reel upload failed: {e}")
        return {
            "success": False,
            "error": f"Upload failed: {str(e)}",
            "error_type": type(e).__name__
        }
```

## Advanced Posting Tools

### 6. Schedule Post Tool

```python
@mcp.tool(
    timeout=TOOL_TIMEOUT_SECONDS,
    title="Schedule Post",
    annotations={"destructiveHint": True, "openWorldHint": True},
    tags={"posting", "scheduling"},
)
async def schedule_post(
    media_path: str,
    caption: str,
    scheduled_time: str,
    media_type: str = "photo",
    account_id: str | None = None,
    ctx: Context = CurrentContext(),
) -> dict[str, Any]:
    """
    Schedule a post for future publication.
    
    Args:
        media_path: Path to media file
        caption: Post caption
        scheduled_time: ISO 8601 timestamp for scheduled posting
        media_type: Type of media (photo, video, carousel, story, reel)
        account_id: Optional account ID to use for the post
    
    Returns:
        Dict with scheduling status and scheduled post information
    """
    from instagram_mcp_server.posting.scheduler import PostScheduler
    
    scheduler = PostScheduler()
    
    # Validate scheduled time
    try:
        from datetime import datetime
        scheduled_dt = datetime.fromisoformat(scheduled_time)
        if scheduled_dt < datetime.now():
            return {"success": False, "error": "Scheduled time must be in the future"}
    except ValueError:
        return {"success": False, "error": "Invalid timestamp format"}
    
    # Validate media
    if media_type == "photo":
        valid, msg = PostingValidator.validate_photo_path(media_path)
    elif media_type in ["video", "reel"]:
        valid, msg = PostingValidator.validate_video_path(media_path)
    else:
        return {"success": False, "error": f"Invalid media type: {media_type}"}
    
    if not valid:
        return {"success": False, "error": msg}
    
    # Schedule the post
    try:
        post = scheduler.schedule_post(
            account_id=account_id or get_active_account().account_id,
            media_path=media_path,
            caption=caption,
            scheduled_time=scheduled_time,
            media_type=media_type
        )
        
        return {
            "success": True,
            "post_id": post.post_id,
            "scheduled_time": post.scheduled_time,
            "media_type": post.media_type,
            "status": post.status,
        }
    except Exception as e:
        logger.error(f"Post scheduling failed: {e}")
        return {
            "success": False,
            "error": f"Scheduling failed: {str(e)}"
        }
```

### 7. Create Post from Template Tool

```python
@mcp.tool(
    timeout=TOOL_TIMEOUT_SECONDS,
    title="Create Post from Template",
    annotations={"destructiveHint": True, "openWorldHint": True},
    tags={"posting", "templates"},
)
async def create_post_from_template(
    template_id: str,
    variables: dict[str, str],
    media_path: str,
    account_id: str | None = None,
    ctx: Context = CurrentContext(),
) -> dict[str, Any]:
    """
    Create a post using a predefined template.
    
    Args:
        template_id: ID of the template to use
        variables: Dictionary of variable replacements for the template
        media_path: Path to media file
        account_id: Optional account ID to use for the post
    
    Returns:
        Dict with template application status and post content
    """
    from instagram_mcp_server.posting.templates import TemplateManager
    
    template_manager = TemplateManager()
    
    # Get template
    template = template_manager.get_template(template_id)
    if not template:
        return {"success": False, "error": f"Template not found: {template_id}"}
    
    # Generate content from template
    try:
        content = template_manager.create_post_from_template(template_id, variables)
        
        # Upload the post with generated content
        client = await get_ready_posting_client(ctx, tool_name="create_post_from_template", account_id=account_id)
        
        # Upload based on media type
        if template.media_type == "photo":
            result = await upload_photo(
                image_path=media_path,
                caption=content["caption"],
                account_id=account_id,
                ctx=tool_guard="create_post_from_template"  # Need to handle this
            )
        elif template.media_type == "video":
            result = await upload_video(
                video_path=media_path,
                caption=content["caption"],
                account_id=account_id,
                ctx=tool_guard="create_post_from_template"
            )
        else:
            return {"success": False, "error": f"Unsupported media type in template: {template.media_type}"}
        
        return {
            "success": True,
            "template_id": template_id,
            "post_result": result,
            "generated_caption": content["caption"],
        }
    except Exception as e:
        logger.error(f"Template application failed: {e}")
        return {
            "success": False,
            "error": f"Template application failed: {str(e)}"
        }
```

## Tool Registration

```python
# instagram_mcp_server/tools/posting_tools.py
from instagram_mcp_server.posting.client import PostingClient
from instagram_mcp_server.dependencies import get_ready_posting_client
from instagram_mcp_server.tools._guard import tool_guard

def register_posting_tools(mcp: FastMCP) -> None:
    """Register all posting-related tools with the MCP server."""
    
    # Register all the tools defined above
    mcp.tool(upload_photo)
    mcp.tool(upload_video)
    mcp.tool(upload_carousel)
    mcp.tool(upload_story)
    mcp.tool(upload_reel)
    mcp.tool(schedule_post)
    mcp.tool(create_post_from_template)
```

## Tool Integration with Server

```python
# instagram_mcp_server/server.py
from instagram_mcp_server.tools.posting_tools import register_posting_tools

def create_mcp_server() -> FastMCP:
    """Create and configure the MCP server with all Instagram tools."""
    mcp = FastMCP(
        "instagram_scraper",
        lifespan=api_lifespan,
        mask_error_details=True,
    )
    mcp.add_middleware(SequentialToolExecutionMiddleware())

    # Register all tools
    register_user_tools(mcp)
    register_post_tools(mcp)
    register_messaging_tools(mcp)
    register_search_tools(mcp)
    register_action_tools(mcp)
    register_transcription_tools(mcp)
    register_gemini_tools(mcp)
    register_multi_account_tools(mcp)
    register_feed_tools(mcp)
    register_trigger_tools(mcp)
    register_posting_tools(mcp)  # NEW: Register posting tools

    # ... rest of server setup
```

## Error Handling Strategy

### Instagram-Specific Error Handling

```python
from instagrapi.exceptions import (
    ChallengeRequired,
    LoginRequired,
    FeedbackRequired,
    RelayRequired,
    SentryBlock,
    IPBlock,
)

def handle_instagrapi_error(error: Exception) -> tuple[bool, str]:
    """Handle instagrapi-specific errors."""
    if isinstance(error, ChallengeRequired):
        return False, "Challenge required - manual intervention needed"
    elif isinstance(error, LoginRequired):
        return False, "Login required - session expired, refresh cookies"
    elif isinstance(error, FeedbackRequired):
        return False, "Feedback required - account action needed"
    elif isinstance(error, RelayRequired):
        return False, "Relay required - account verification needed"
    elif isinstance(error, SentryBlock):
        return False, "Sentry block - account temporarily blocked"
    elif isinstance(error, IPBlock):
        return False, "IP block - IP address blocked by Instagram"
    else:
        return False, f"Unknown error: {str(error)}"
```

## Tool Return Format

All posting tools return consistent format:

```python
{
    "success": bool,
    "post_id": str | None,
    "post_shortcode": str | None,
    "post_url": str | None,
    "media_type": str,
    "taken_at": str | None,
    "caption": str | None,
    "error": str | None,
    "error_type": str | None
}
```

## Usage Examples

### Basic Photo Upload
```python
result = await mcp.call_tool("upload_photo", {
    "image_path": "/path/to/photo.jpg",
    "caption": "Beautiful sunset today! #photography #sunset",
    "account_id": "business_account_abc"
})
```

### Video Upload with Tags
```python
result = await mcp.call_tool("upload_video", {
    "video_path": "/path/to/video.mp4",
    "caption": "Behind the scenes of our photoshoot 🎬",
    "user_tags": ["photographer1", "model1"],
    "location_id": "123456789",
    "account_id": "business_account_abc"
})
```

### Carousel Upload
```python
result = await mcp.call_tool("upload_carousel", {
    "media_paths": [
        "/path/to/photo1.jpg",
        "/path/to/photo2.jpg",
        "/path/to/photo3.jpg"
    ],
    "caption": "Trip recap with the team! #travel #adventure",
    "account_id": "business_account_abc"
})
```

### Story with Link
```python
result = await mcp.call_tool("upload_story", {
    "media_path": "/path/to/story.jpg",
    "caption": "Check out our new product! 🚀",
    "links": ["https://example.com/product"],
    "mentions": ["brand_partner"],
    "account_id": "business_account_abc"
})
```

This design provides a comprehensive set of MCP tools for media posting that integrates seamlessly with the existing architecture while following established patterns.