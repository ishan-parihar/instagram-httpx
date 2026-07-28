"""
Feed browsing functionality for Instagram MCP Server.

Provides tools for browsing the home feed, timeline, and discovering
content from followed accounts for AI agent workflows.
"""

from __future__ import annotations

import logging
from typing import Any
from dataclasses import dataclass

from instagram_mcp_server.scraping.api_client import InstagramAPIClient
from instagram_mcp_server.callbacks import ProgressCallback

logger = logging.getLogger(__name__)


@dataclass
class FeedPost:
    """Structured data for a feed post."""
    id: str
    shortcode: str
    url: str
    thumbnail_url: str
    media_type: int  # 1=image, 2=video, 8=carousel
    caption: str | None = None
    likes_count: int = 0
    comments_count: int = 0
    timestamp: str = ""
    username: str = ""
    user_full_name: str = ""
    user_profile_pic: str = ""
    is_video: bool = False
    video_url: str = ""
    play_count: int = 0
    carousel_media: list[dict] = None  # type: ignore


class FeedBrowser:
    """Browser for Instagram home feed and timeline content."""
    
    def __init__(self, client: InstagramAPIClient):
        self._client = client
    
    async def get_home_feed(
        self,
        max_posts: int = 50,
        callbacks: ProgressCallback | None = None,
    ) -> dict[str, Any]:
        """Get the home feed (posts from followed accounts).
        
        Args:
            max_posts: Maximum number of posts to retrieve
            callbacks: Optional progress callbacks
            
        Returns:
            Dict with feed data including posts list and metadata
        """
        if callbacks:
            await callbacks.on_progress("Fetching home feed", 0)
        
        try:
            # Use the API client to fetch home feed
            # For now, return a placeholder since get_home_feed might not be implemented
            # In production, this would call the actual API method
            feed_data = {"items": []}  # Placeholder until API client has this method
            
            if callbacks:
                await callbacks.on_progress("Processing feed items", 50)
            
            # Process feed items into structured format
            posts = []
            for item in feed_data.get("items", []):
                try:
                    post = self._process_feed_item(item)
                    if post:
                        posts.append(post)
                except Exception as e:
                    logger.warning(f"Failed to process feed item: {e}")
                    continue
            
            if callbacks:
                await callbacks.on_progress("Complete", 100)
            
            return {
                "url": "https://www.instagram.com/",
                "sections": {
                    "home_feed": f"Found {len(posts)} posts from your feed"
                },
                "posts": [self._post_to_dict(post) for post in posts],
                "total_posts": len(posts),
            }
            
        except Exception as e:
            logger.error(f"Failed to fetch home feed: {e}")
            return {
                "url": "https://www.instagram.com/",
                "sections": {
                    "home_feed": f"Error fetching feed: {str(e)}"
                },
                "posts": [],
                "total_posts": 0,
                "error": str(e),
            }
    
    async def get_discover_feed(
        self,
        max_posts: int = 50,
        callbacks: ProgressCallback | None = None,
    ) -> dict[str, Any]:
        """Get the discover/explore feed.
        
        Args:
            max_posts: Maximum number of posts to retrieve
            callbacks: Optional progress callbacks
            
        Returns:
            Dict with discover feed data
        """
        if callbacks:
            await callbacks.on_progress("Fetching discover feed", 0)
        
        try:
            # Use the API client to fetch discover feed
            # For now, return a placeholder since get_discover_feed might not be implemented
            # In production, this would call the actual API method
            discover_data = {"items": []}  # Placeholder until API client has this method
            
            if callbacks:
                await callbacks.on_progress("Processing discover items", 50)
            
            posts = []
            for item in discover_data.get("items", []):
                try:
                    post = self._process_feed_item(item)
                    if post:
                        posts.append(post)
                except Exception as e:
                    logger.warning(f"Failed to process discover item: {e}")
                    continue
            
            if callbacks:
                await callbacks.on_progress("Complete", 100)
            
            return {
                "url": "https://www.instagram.com/explore/",
                "sections": {
                    "discover_feed": f"Found {len(posts)} posts from discover"
                },
                "posts": [self._post_to_dict(post) for post in posts],
                "total_posts": len(posts),
            }
            
        except Exception as e:
            logger.error(f"Failed to fetch discover feed: {e}")
            return {
                "url": "https://www.instagram.com/explore/",
                "sections": {
                    "discover_feed": f"Error fetching discover: {str(e)}"
                },
                "posts": [],
                "total_posts": 0,
                "error": str(e),
            }
    
    async def get_user_timeline(
        self,
        username: str,
        max_posts: int = 50,
        callbacks: ProgressCallback | None = None,
    ) -> dict[str, Any]:
        """Get posts from a specific user's timeline.
        
        Args:
            username: Instagram username
            max_posts: Maximum number of posts to retrieve
            callbacks: Optional progress callbacks
            
        Returns:
            Dict with user timeline data
        """
        if callbacks:
            await callbacks.on_progress(f"Fetching timeline for @{username}", 0)
        
        try:
            # This would use the existing user posts functionality
            # For now, we'll use the API client
            # In production, this would call the actual API method
            timeline_data = {"items": []}  # Placeholder until API client has this method
            
            if callbacks:
                await callbacks.on_progress("Processing timeline items", 50)
            
            posts = []
            for item in timeline_data.get("items", []):
                try:
                    post = self._process_feed_item(item)
                    if post:
                        posts.append(post)
                except Exception as e:
                    logger.warning(f"Failed to process timeline item: {e}")
                    continue
            
            if callbacks:
                await callbacks.on_progress("Complete", 100)
            
            return {
                "url": f"https://www.instagram.com/{username}/",
                "sections": {
                    "user_timeline": f"Found {len(posts)} posts from @{username}"
                },
                "posts": [self._post_to_dict(post) for post in posts],
                "total_posts": len(posts),
            }
            
        except Exception as e:
            logger.error(f"Failed to fetch user timeline: {e}")
            return {
                "url": f"https://www.instagram.com/{username}/",
                "sections": {
                    "user_timeline": f"Error fetching timeline: {str(e)}"
                },
                "posts": [],
                "total_posts": 0,
                "error": str(e),
            }
    
    def _process_feed_item(self, item: dict) -> FeedPost | None:
        """Process a feed item into structured FeedPost format."""
        try:
            # Extract media or user info from the feed item
            # This is a simplified version - actual implementation would need
            # to handle various feed item formats
            
            media_or_ad = item.get("media_or_ad", {})
            if not media_or_ad:
                return None
            
            # Basic post data
            post_id = media_or_ad.get("id", "")
            if not post_id:
                return None
            
            shortcode = media_or_ad.get("code", "")
            if not shortcode:
                shortcode = post_id  # Fallback
            
            # User info
            user = media_or_ad.get("user", {})
            username = user.get("username", "")
            full_name = user.get("full_name", "")
            profile_pic = user.get("profile_pic_url", "")
            
            # Media info
            image_versions = media_or_ad.get("image_versions2", {})
            candidates = image_versions.get("candidates", [])
            thumbnail_url = candidates[0].get("url", "") if candidates else ""
            
            media_type = media_or_ad.get("media_type", 1)
            
            # Caption
            caption_data = media_or_ad.get("caption", {})
            caption = caption_data.get("text", "") if caption_data else None
            
            # Engagement metrics
            like_count = media_or_ad.get("like_count", 0)
            comment_count = media_or_ad.get("comment_count", 0)
            
            # Video info
            is_video = media_or_ad.get("media_type") == 2
            video_url = media_or_ad.get("video_versions", [{}])[0].get("url", "") if is_video else ""
            play_count = media_or_ad.get("view_count", 0) if is_video else 0
            
            # Carousel info
            carousel_media = []
            if media_type == 8:  # Carousel
                carousel_data = media_or_ad.get("carousel_media", [])
                for carousel_item in carousel_data:
                    carousel_media.append({
                        "id": carousel_item.get("id", ""),
                        "image_url": carousel_item.get("image_versions2", {}).get("candidates", [{}])[0].get("url", ""),
                    })
            
            # Timestamp
            taken_at = media_or_ad.get("taken_at", 0)
            from datetime import datetime
            timestamp = datetime.fromtimestamp(taken_at).isoformat() if taken_at else ""
            
            return FeedPost(
                id=post_id,
                shortcode=shortcode,
                url=f"https://www.instagram.com/p/{shortcode}/",
                thumbnail_url=thumbnail_url,
                media_type=media_type,
                caption=caption,
                likes_count=like_count,
                comments_count=comment_count,
                timestamp=timestamp,
                username=username,
                user_full_name=full_name,
                user_profile_pic=profile_pic,
                is_video=is_video,
                video_url=video_url,
                play_count=play_count,
                carousel_media=carousel_media,
            )
            
        except Exception as e:
            logger.warning(f"Failed to process feed item: {e}")
            return None
    
    def _post_to_dict(self, post: FeedPost) -> dict[str, Any]:
        """Convert FeedPost to dictionary for JSON serialization."""
        return {
            "id": post.id,
            "shortcode": post.shortcode,
            "url": post.url,
            "thumbnail_url": post.thumbnail_url,
            "media_type": post.media_type,
            "caption": post.caption,
            "likes_count": post.likes_count,
            "comments_count": post.comments_count,
            "timestamp": post.timestamp,
            "username": post.username,
            "user_full_name": post.user_full_name,
            "user_profile_pic": post.user_profile_pic,
            "is_video": post.is_video,
            "video_url": post.video_url,
            "play_count": post.play_count,
            "carousel_media": post.carousel_media or [],
        }