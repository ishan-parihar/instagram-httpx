"""
Instagram posting tools for MCP.

Provides MCP tools for uploading photos, videos, carousels, stories, and reels
to Instagram with multi-account support.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from PIL import Image
from fastmcp import Context
from fastmcp.dependencies import CurrentContext

from instagram_mcp_server.constants import TOOL_TIMEOUT_SECONDS
from instagram_mcp_server.dependencies import get_ready_posting_client
from instagram_mcp_server.multi_account import (
    check_account_posting_limits,
    get_active_account,
    record_post_attempt,
)
from instagram_mcp_server.posting.client import handle_instagrapi_error
from instagram_mcp_server.posting.media_processor import MediaProcessor
from instagram_mcp_server.posting.validators import PostingValidator
from instagram_mcp_server.tools._guard import tool_guard

logger = logging.getLogger(__name__)


def register_posting_tools(mcp) -> None:
    """Register all posting-related tools with the MCP server."""
    
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
        aspect_ratio: str = "4:5",
        fit_mode: str = "auto",  # "auto" smart detection, "fit" letterbox/pillarbox, "crop" center crop
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
            aspect_ratio: Target aspect ratio ("4:5", "1:1", "1.91:1", "auto")
            fit_mode: Processing mode ("auto" smart detection, "fit" letterbox/pillarbox, "crop" center crop)
        
        Returns:
            Dict with upload status, post URL, and media information
        """
        logger.info(f"Upload photo requested: {image_path} with aspect ratio: {aspect_ratio}, fit mode: {fit_mode}")
        
        # Get account ID if not provided
        if not account_id:
            active = get_active_account()
            if active:
                account_id = active.account_id
        
        # Check account posting limits
        if account_id:
            can_post, reason = check_account_posting_limits(account_id)
            if not can_post:
                return {"success": False, "error": reason}
        
        # Validate inputs
        valid, msg = PostingValidator.validate_photo_path(image_path)
        if not valid:
            return {"success": False, "error": msg}
        
        valid, msg = PostingValidator.validate_caption(caption)
        if not valid:
            return {"success": False, "error": msg}
        
        try:
            # Get posting client
            client = await get_ready_posting_client(
                ctx, tool_name="upload_photo", account_id=account_id
            )
            
            # Process image with smart aspect ratio handling
            try:
                # Handle aspect ratio parameter
                if aspect_ratio == "auto":
                    # Let smart processing auto-detect the best ratio
                    processed_path = MediaProcessor.process_image_smart(
                        image_path, 
                        media_type="feed",
                        fit_mode=fit_mode
                    )
                else:
                    # Convert aspect ratio string to tuple
                    aspect_map = {
                        "4:5": (4, 5),
                        "1:1": (1, 1),
                        "1.91:1": (1.91, 1),
                    }
                    target_aspect = aspect_map.get(aspect_ratio, (4, 5))
                    
                    # Process with specific aspect ratio
                    if fit_mode == "fit":
                        # Use letterbox/pillarbox mode
                        processed_path = MediaProcessor.process_image_flexible(
                            image_path, target_aspect=target_aspect, force_aspect=False
                        )
                        # Then apply fit mode using private method
                        img = Image.open(processed_path)
                        img = MediaProcessor._fit_to_aspect_ratio(img, target_aspect)
                        # Manually save the processed image
                        from tempfile import gettempdir
                        from pathlib import Path
                        temp_dir = Path(gettempdir()) / "instagram-media"
                        temp_dir.mkdir(exist_ok=True)
                        import hashlib
                        hash_val = hashlib.md5(image_path.encode()).hexdigest()[:8]
                        processed_path = temp_dir / f"processed_fit_{hash_val}.jpg"
                        img.save(str(processed_path), 'JPEG', quality=85)
                    elif fit_mode == "crop":
                        # Use crop mode
                        processed_path = MediaProcessor.process_image_flexible(
                            image_path, target_aspect=target_aspect, force_aspect=True
                        )
                    else:  # auto mode
                        processed_path = MediaProcessor.process_image_smart(
                            image_path, 
                            media_type="feed",
                            fit_mode="auto"
                        )
                
                logger.info(f"Smart processed image: {processed_path}")
            except Exception as e:
                logger.error(f"Image processing failed: {e}")
                return {"success": False, "error": f"Image processing failed: {str(e)}"}
            
            # Upload using instagrapi
            # Build kwargs for instagrapi
            upload_kwargs = {}
            if location_id:
                upload_kwargs["location"] = location_id
            if user_tags:
                upload_kwargs["usertags"] = user_tags
            if extra_data:
                upload_kwargs["extra_data"] = extra_data
            if schedule_at:
                upload_kwargs["schedule_at"] = schedule_at
            if share_to_facebook:
                upload_kwargs["share_to_facebook"] = share_to_facebook
            if share_to_threads:
                upload_kwargs["share_to_threads"] = share_to_threads
            
            media = client.upload_photo(
                path=processed_path,
                caption=caption,
                **upload_kwargs
            )
            
            # Record successful post
            if account_id:
                record_post_attempt(
                    account_id=account_id,
                    media_type="photo",
                    success=True,
                    post_id=str(media.pk)
                )
            
            return {
                "success": True,
                "post_id": str(media.pk),
                "post_shortcode": media.code,
                "post_url": f"https://www.instagram.com/p/{media.code}/",
                "media_type": "photo",
                "taken_at": str(media.taken_at) if hasattr(media, 'taken_at') else None,
                "caption": caption,
            }
            
        except Exception as e:
            logger.error(f"Photo upload failed: {e}")
            
            # Record failed post
            if account_id:
                record_post_attempt(
                    account_id=account_id,
                    media_type="photo",
                    success=False,
                    error_message=str(e)
                )
            
            # Handle Instagram-specific errors
            success, error_msg = handle_instagrapi_error(e)
            return {
                "success": False,
                "error": error_msg if not success else str(e),
                "error_type": type(e).__name__
            }
    
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
        location_id: str | None = None,
        user_tags: list[str] | None = None,
        extra_data: dict[str, str] | None = None,
        schedule_at: str | None = None,
        share_to_facebook: bool = False,
        share_to_threads: bool = False,
        max_duration: int | None = None,
        ctx: Context = CurrentContext(),
    ) -> dict[str, Any]:
        """
        Upload a video to Instagram feed.
        
        Args:
            video_path: Path to video file (MP4/MOV, max 180 seconds)
            caption: Video caption (max 2200 characters)
            account_id: Optional account ID to use for the upload
            location_id: Optional Instagram location ID for tagging
            user_tags: Optional list of usernames to tag in the video
            extra_data: Optional additional metadata for the post
            schedule_at: Optional ISO 8601 timestamp for scheduled posting
            share_to_facebook: Whether to cross-post to Facebook
            share_to_threads: Whether to cross-post to Threads
            max_duration: Custom max duration in seconds (overrides 180s default)
        
        Returns:
            Dict with upload status, post URL, and media information
        """
        logger.info(f"Upload video requested: {video_path}")
        
        # Get account ID if not provided
        if not account_id:
            active = get_active_account()
            if active:
                account_id = active.account_id
        
        # Check account posting limits
        if account_id:
            can_post, reason = check_account_posting_limits(account_id)
            if not can_post:
                return {"success": False, "error": reason}
        
        # Validate inputs
        valid, msg = PostingValidator.validate_video_path(video_path)
        if not valid:
            return {"success": False, "error": msg}
        
        valid, msg = PostingValidator.validate_caption(caption)
        if not valid:
            return {"success": False, "error": msg}
        
        try:
            # Get posting client
            client = await get_ready_posting_client(
                ctx, tool_name="upload_video", account_id=account_id
            )
            
            # Process video with smart aspect ratio handling
            try:
                processed_path, thumbnail_path = MediaProcessor.process_video_smart(
                    video_path, 
                    media_type="feed",
                    max_duration=max_duration
                )
                logger.info(f"Smart processed video: {processed_path}, thumbnail: {thumbnail_path}")
            except Exception as e:
                logger.error(f"Video processing failed: {e}")
                return {"success": False, "error": f"Video processing failed: {str(e)}"}
            
            # Upload using instagrapi
            # Build kwargs for instagrapi
            upload_kwargs = {}
            if location_id:
                upload_kwargs["location"] = location_id
            if user_tags:
                upload_kwargs["usertags"] = user_tags
            if extra_data:
                upload_kwargs["extra_data"] = extra_data
            if schedule_at:
                upload_kwargs["schedule_at"] = schedule_at
            if share_to_facebook:
                upload_kwargs["share_to_facebook"] = share_to_facebook
            if share_to_threads:
                upload_kwargs["share_to_threads"] = share_to_threads
            if thumbnail_path:
                upload_kwargs["thumbnail"] = Path(thumbnail_path)
            
            media = client.upload_video(
                path=processed_path,
                caption=caption,
                **upload_kwargs
            )
            
            # Record successful post
            if account_id:
                record_post_attempt(
                    account_id=account_id,
                    media_type="video",
                    success=True,
                    post_id=str(media.pk)
                )
            
            return {
                "success": True,
                "post_id": str(media.pk),
                "post_shortcode": media.code,
                "post_url": f"https://www.instagram.com/p/{media.code}/",
                "media_type": "video",
                "taken_at": str(media.taken_at) if hasattr(media, 'taken_at') else None,
                "caption": caption,
            }
            
        except Exception as e:
            logger.error(f"Video upload failed: {e}")
            
            # Record failed post
            if account_id:
                record_post_attempt(
                    account_id=account_id,
                    media_type="video",
                    success=False,
                    error_message=str(e)
                )
            
            # Handle Instagram-specific errors
            success, error_msg = handle_instagrapi_error(e)
            return {
                "success": False,
                "error": error_msg if not success else str(e),
                "error_type": type(e).__name__
            }
    
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
        Upload a carousel (album) to Instagram feed.
        
        Args:
            media_paths: List of paths to image files (JPG/PNG, 2-10 items)
            caption: Carousel caption (max 2200 characters)
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
        logger.info(f"Upload carousel requested: {len(media_paths)} items")
        
        # Get account ID if not provided
        if not account_id:
            active = get_active_account()
            if active:
                account_id = active.account_id
        
        # Check account posting limits
        if account_id:
            can_post, reason = check_account_posting_limits(account_id)
            if not can_post:
                return {"success": False, "error": reason}
        
        # Validate inputs
        valid, msg = PostingValidator.validate_carousel_paths(media_paths)
        if not valid:
            return {"success": False, "error": msg}
        
        valid, msg = PostingValidator.validate_caption(caption)
        if not valid:
            return {"success": False, "error": msg}
        
        try:
            # Get posting client
            client = await get_ready_posting_client(
                ctx, tool_name="upload_carousel", account_id=account_id
            )
            
            # Process images with smart aspect ratio handling
            processed_paths = []
            for path in media_paths:
                try:
                    processed_path = MediaProcessor.process_image_smart(
                        path, 
                        media_type="carousel",
                        fit_mode="auto"
                    )
                    processed_paths.append(processed_path)
                except Exception as e:
                    logger.error(f"Image processing failed for {path}: {e}")
                    return {"success": False, "error": f"Image processing failed for {path}: {str(e)}"}
            
            logger.info(f"Processed {len(processed_paths)} carousel images")
            
            # Upload using instagrapi
            # Build kwargs for instagrapi
            upload_kwargs = {}
            if location_id:
                upload_kwargs["location"] = location_id
            if user_tags:
                upload_kwargs["usertags"] = user_tags
            if extra_data:
                upload_kwargs["extra_data"] = extra_data
            if schedule_at:
                upload_kwargs["schedule_at"] = schedule_at
            if share_to_facebook:
                upload_kwargs["share_to_facebook"] = share_to_facebook
            if share_to_threads:
                upload_kwargs["share_to_threads"] = share_to_threads
            
            media = client.upload_carousel(
                paths=processed_paths,
                caption=caption,
                **upload_kwargs
            )
            
            # Record successful post
            if account_id:
                record_post_attempt(
                    account_id=account_id,
                    media_type="carousel",
                    success=True,
                    post_id=str(media.pk)
                )
            
            return {
                "success": True,
                "post_id": str(media.pk),
                "post_shortcode": media.code,
                "post_url": f"https://www.instagram.com/p/{media.code}/",
                "media_type": "carousel",
                "item_count": len(media_paths),
                "taken_at": str(media.taken_at) if hasattr(media, 'taken_at') else None,
                "caption": caption,
            }
            
        except Exception as e:
            logger.error(f"Carousel upload failed: {e}")
            
            # Record failed post
            if account_id:
                record_post_attempt(
                    account_id=account_id,
                    media_type="carousel",
                    success=False,
                    error_message=str(e)
                )
            
            # Handle Instagram-specific errors
            success, error_msg = handle_instagrapi_error(e)
            return {
                "success": False,
                "error": error_msg if not success else str(e),
                "error_type": type(e).__name__
            }
    
    @mcp.tool(
        timeout=TOOL_TIMEOUT_SECONDS,
        title="Upload Story",
        annotations={"destructiveHint": True, "openWorldHint": True},
        tags={"posting", "media", "story"},
    )
    @tool_guard("upload_story")
    async def upload_story(
        media_path: str,
        media_type: str = "photo",
        caption: str | None = None,
        account_id: str | None = None,
        mentions: list[str] | None = None,
        hashtags: list[str] | None = None,
        links: list[str] | None = None,
        max_duration: int | None = None,
        ctx: Context = CurrentContext(),
    ) -> dict[str, Any]:
        """
        Upload a story to Instagram.
        
        Args:
            media_path: Path to media file (JPG/PNG for photo, MP4/MOV for video)
            media_type: Type of media ("photo" or "video")
            caption: Optional caption for the story
            account_id: Optional account ID to use for the upload
            mentions: Optional list of usernames to mention in the story
            hashtags: Optional list of hashtags to include in the story
            links: Optional list of URLs to include as link stickers
            max_duration: Custom max duration in seconds for videos (overrides 60s default)
        
        Returns:
            Dict with upload status and story information
        """
        logger.info(f"Upload story requested: {media_path} ({media_type})")
        
        # Get account ID if not provided
        if not account_id:
            active = get_active_account()
            if active:
                account_id = active.account_id
        
        # Check account posting limits
        if account_id:
            can_post, reason = check_account_posting_limits(account_id)
            if not can_post:
                return {"success": False, "error": reason}
        
        # Validate media type
        if media_type not in ["photo", "video"]:
            return {"success": False, "error": "media_type must be 'photo' or 'video'"}
        
        # Validate inputs
        if media_type == "photo":
            valid, msg = PostingValidator.validate_photo_path(media_path)
        else:
            valid, msg = PostingValidator.validate_video_path(media_path, is_story=True)
        
        if not valid:
            return {"success": False, "error": msg}
        
        try:
            # Get posting client
            client = await get_ready_posting_client(
                ctx, tool_name="upload_story", account_id=account_id
            )
            
            # Process media with smart aspect ratio handling
            if media_type == "photo":
                try:
                    processed_path = MediaProcessor.process_image_smart(
                        media_path, 
                        media_type="stories",
                        fit_mode="fit"  # Stories use fit mode (letterbox) for aesthetic reasons
                    )
                    logger.info(f"Smart processed story photo: {processed_path}")
                except Exception as e:
                    logger.error(f"Image processing failed: {e}")
                    return {"success": False, "error": f"Image processing failed: {str(e)}"}
            else:
                try:
                    processed_path, thumbnail_path = MediaProcessor.process_video_smart(
                        media_path, 
                        media_type="stories",
                        max_duration=max_duration
                    )
                    logger.info(f"Smart processed story video: {processed_path}")
                except Exception as e:
                    logger.error(f"Video processing failed: {e}")
                    return {"success": False, "error": f"Video processing failed: {str(e)}"}
            
            # Upload using instagrapi
            # Build kwargs for instagrapi
            upload_kwargs = {}
            if caption:
                upload_kwargs["caption"] = caption
            if mentions:
                upload_kwargs["mentions"] = mentions
            if hashtags:
                upload_kwargs["hashtags"] = hashtags
            if links:
                upload_kwargs["links"] = links
            
            if media_type == "photo":
                story = client.upload_story_photo(path=processed_path, **upload_kwargs)
            else:
                story = client.upload_story_video(path=processed_path, **upload_kwargs)
            
            # Record successful post
            if account_id:
                record_post_attempt(
                    account_id=account_id,
                    media_type="story",
                    success=True,
                    post_id=str(story.pk)
                )
            
            return {
                "success": True,
                "story_id": str(story.pk),
                "media_type": media_type,
                "taken_at": str(story.taken_at) if hasattr(story, 'taken_at') else None,
                "caption": caption,
            }
            
        except Exception as e:
            logger.error(f"Story upload failed: {e}")
            
            # Record failed post
            if account_id:
                record_post_attempt(
                    account_id=account_id,
                    media_type="story",
                    success=False,
                    error_message=str(e)
                )
            
            # Handle Instagram-specific errors
            success, error_msg = handle_instagrapi_error(e)
            return {
                "success": False,
                "error": error_msg if not success else str(e),
                "error_type": type(e).__name__
            }
    
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
        location_id: str | None = None,
        user_tags: list[str] | None = None,
        extra_data: dict[str, str] | None = None,
        share_to_facebook: bool = False,
        share_to_threads: bool = False,
        ctx: Context = CurrentContext(),
    ) -> dict[str, Any]:
        """
        Upload a reel to Instagram.
        
        Args:
            video_path: Path to video file (MP4/MOV, max 60 seconds)
            caption: Reel caption (max 2200 characters)
            account_id: Optional account ID to use for the upload
            location_id: Optional Instagram location ID for tagging
            user_tags: Optional list of usernames to tag in the reel
            extra_data: Optional additional metadata for the post
            share_to_facebook: Whether to cross-post to Facebook
            share_to_threads: Whether to cross-post to Threads
        
        Returns:
            Dict with upload status, post URL, and media information
        """
        logger.info(f"Upload reel requested: {video_path}")
        
        # Get account ID if not provided
        if not account_id:
            active = get_active_account()
            if active:
                account_id = active.account_id
        
        # Check account posting limits
        if account_id:
            can_post, reason = check_account_posting_limits(account_id)
            if not can_post:
                return {"success": False, "error": reason}
        
        # Validate inputs
        valid, msg = PostingValidator.validate_video_path(video_path)
        if not valid:
            return {"success": False, "error": msg}
        
        valid, msg = PostingValidator.validate_caption(caption)
        if not valid:
            return {"success": False, "error": msg}
        
        try:
            # Get posting client
            client = await get_ready_posting_client(
                ctx, tool_name="upload_reel", account_id=account_id
            )
            
            # Process video if needed
            try:
                processed_path, thumbnail_path = MediaProcessor.process_video(video_path)
                logger.info(f"Processed reel video: {processed_path}, thumbnail: {thumbnail_path}")
            except Exception as e:
                logger.error(f"Video processing failed: {e}")
                return {"success": False, "error": f"Video processing failed: {str(e)}"}
            
            # Upload using instagrapi
            # Build kwargs for instagrapi
            upload_kwargs = {}
            if location_id:
                upload_kwargs["location"] = location_id
            if user_tags:
                upload_kwargs["usertags"] = user_tags
            if extra_data:
                upload_kwargs["extra_data"] = extra_data
            if share_to_facebook:
                upload_kwargs["share_to_facebook"] = share_to_facebook
            if share_to_threads:
                upload_kwargs["share_to_threads"] = share_to_threads
            if thumbnail_path:
                upload_kwargs["thumbnail"] = Path(thumbnail_path)
            
            media = client.upload_reel(
                path=processed_path,
                caption=caption,
                **upload_kwargs
            )
            
            # Record successful post
            if account_id:
                record_post_attempt(
                    account_id=account_id,
                    media_type="reel",
                    success=True,
                    post_id=str(media.pk)
                )
            
            return {
                "success": True,
                "post_id": str(media.pk),
                "post_shortcode": media.code,
                "post_url": f"https://www.instagram.com/reel/{media.code}/",
                "media_type": "reel",
                "taken_at": str(media.taken_at) if hasattr(media, 'taken_at') else None,
                "caption": caption,
            }
            
        except Exception as e:
            logger.error(f"Reel upload failed: {e}")
            
            # Record failed post
            if account_id:
                record_post_attempt(
                    account_id=account_id,
                    media_type="reel",
                    success=False,
                    error_message=str(e)
                )
            
            # Handle Instagram-specific errors
            success, error_msg = handle_instagrapi_error(e)
            return {
                "success": False,
                "error": error_msg if not success else str(e),
                "error_type": type(e).__name__
            }