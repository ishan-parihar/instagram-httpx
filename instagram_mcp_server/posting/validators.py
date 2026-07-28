"""
Media validators for Instagram posting.

Validates media files, captions, and posting parameters to ensure they meet
Instagram's requirements.
"""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class PostingValidator:
    """Validate posting parameters and media."""
    
    # Instagram specifications (updated 2025)
    MAX_IMAGE_SIZE = 1080  # pixels
    MAX_VIDEO_DURATION = 180  # seconds for Reels/Feed (3 minutes)
    MAX_STORY_DURATION = 60  # seconds for Stories
    MAX_CAPTION_LENGTH = 2200  # characters
    MAX_CAROUSEL_ITEMS = 10
    MIN_CAROUSEL_ITEMS = 2
    
    VALID_IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png']
    VALID_VIDEO_EXTENSIONS = ['.mp4', '.mov', '.avi']
    
    # Valid aspect ratios for different media types (updated 2025)
    VALID_ASPECT_RATIOS = {
        'feed': [(4, 5), (1, 1), (1.91, 1)],  # 4:5 portrait, 1:1 square, 1.91:1 landscape
        'reels': [(9, 16)],  # 9:16 vertical only
        'stories': [(9, 16)],  # 9:16 vertical only
        'carousel': [(4, 5), (1, 1)],  # 4:5 portrait, 1:1 square (all slides must match)
    }
    
    @staticmethod
    def validate_photo_path(image_path: str) -> tuple[bool, str]:
        """Validate photo path and file.
        
        Args:
            image_path: Path to image file
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        path = Path(image_path)
        
        if not path.exists():
            return False, f"Image file not found: {image_path}"
        
        if not path.is_file():
            return False, f"Path is not a file: {image_path}"
        
        # Check file extension
        if path.suffix.lower() not in PostingValidator.VALID_IMAGE_EXTENSIONS:
            return False, (
                f"Invalid image format: {path.suffix}. "
                f"Supported: {PostingValidator.VALID_IMAGE_EXTENSIONS}"
            )
        
        return True, ""
    
    @staticmethod
    def validate_video_path(video_path: str, is_story: bool = False) -> tuple[bool, str]:
        """Validate video path and file.
        
        Args:
            video_path: Path to video file
            is_story: Whether this is for a story (affects duration limits)
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        path = Path(video_path)
        
        if not path.exists():
            return False, f"Video file not found: {video_path}"
        
        if not path.is_file():
            return False, f"Path is not a file: {video_path}"
        
        # Check file extension
        if path.suffix.lower() not in PostingValidator.VALID_VIDEO_EXTENSIONS:
            return False, (
                f"Invalid video format: {path.suffix}. "
                f"Supported: {PostingValidator.VALID_VIDEO_EXTENSIONS}"
            )
        
        # Note: Duration validation requires actually processing the video
        # This is done in media_processor.py
        
        return True, ""
    
    @staticmethod
    def validate_caption(caption: str) -> tuple[bool, str]:
        """Validate caption text.
        
        Args:
            caption: Caption text to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not caption or not caption.strip():
            return False, "Caption cannot be empty"
        
        if len(caption) > PostingValidator.MAX_CAPTION_LENGTH:
            return False, (
                f"Caption too long: {len(caption)} characters "
                f"(max {PostingValidator.MAX_CAPTION_LENGTH})"
            )
        
        return True, ""
    
    @staticmethod
    def validate_carousel_paths(paths: list[str]) -> tuple[bool, str]:
        """Validate carousel media paths.
        
        Args:
            paths: List of media file paths
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if len(paths) < PostingValidator.MIN_CAROUSEL_ITEMS:
            return False, (
                f"Carousel must have at least {PostingValidator.MIN_CAROUSEL_ITEMS} "
                f"media items (got {len(paths)})"
            )
        
        if len(paths) > PostingValidator.MAX_CAROUSEL_ITEMS:
            return False, (
                f"Carousel can have at most {PostingValidator.MAX_CAROUSEL_ITEMS} "
                f"media items (got {len(paths)})"
            )
        
        for path in paths:
            valid, msg = PostingValidator.validate_photo_path(path)
            if not valid:
                return False, f"Invalid carousel item: {msg}"
        
        return True, ""
    
    @staticmethod
    def validate_account_id(account_id: str | None) -> tuple[bool, str]:
        """Validate account ID.
        
        Args:
            account_id: Account ID to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if account_id is None:
            return True, ""  # Optional parameter is valid
        
        if not account_id or not account_id.strip():
            return False, "Account ID cannot be empty"
        
        return True, ""
    
    @staticmethod
    def validate_scheduled_time(scheduled_time: str) -> tuple[bool, str]:
        """Validate scheduled time format.
        
        Args:
            scheduled_time: ISO 8601 timestamp string
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        from datetime import datetime
        
        try:
            scheduled_dt = datetime.fromisoformat(scheduled_time)
            if scheduled_dt < datetime.now():
                return False, "Scheduled time must be in the future"
            return True, ""
        except ValueError:
            return False, "Invalid timestamp format (expected ISO 8601)"
    
    @staticmethod
    def validate_aspect_ratio(
        width: int,
        height: int,
        media_type: str = "feed"
    ) -> tuple[bool, str]:
        """Validate aspect ratio for media type.
        
        Args:
            width: Image/video width in pixels
            height: Image/video height in pixels
            media_type: Type of media ("feed", "reels", "stories")
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if height == 0:
            return False, "Height cannot be zero"
        
        aspect_ratio = width / height
        
        # Get valid ratios for media type
        valid_ratios = PostingValidator.VALID_ASPECT_RATIOS.get(media_type, [(4, 5), (1, 1), (16, 9)])
        
        # Calculate allowed ratio range
        # For feed: accept 4:5 (0.8) to 1.91:1 (1.91)
        # For reels: accept 9:16 (0.5625) only
        # For stories: accept 9:16 (0.5625) only
        # For carousel: accept 4:5 (0.8) to 1:1 (1.0)
        
        if media_type == "feed":
            # Accept 4:5 (0.8) to 1.91:1 (1.91)
            min_ratio, max_ratio = 0.8, 1.91
        elif media_type == "reels":
            # Accept 9:16 (0.5625) only
            min_ratio, max_ratio = 0.5625, 0.5625
        elif media_type == "stories":
            # Accept 9:16 (0.5625) only
            min_ratio, max_ratio = 0.5625, 0.5625
        elif media_type == "carousel":
            # Accept 4:5 (0.8) to 1:1 (1.0)
            min_ratio, max_ratio = 0.8, 1.0
        else:
            # Default to feed range
            min_ratio, max_ratio = 0.8, 1.91
        
        if not (min_ratio <= aspect_ratio <= max_ratio):
            return False, (
                f"Invalid aspect ratio {width}:{height} ({aspect_ratio:.2f}) for {media_type}. "
                f"Accepted range: {min_ratio:.2f} to {max_ratio:.2f}"
            )
        
        return True, ""