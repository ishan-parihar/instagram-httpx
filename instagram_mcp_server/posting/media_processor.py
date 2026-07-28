"""
Media processor for Instagram posting.

Handles image and video preprocessing for Instagram specifications.
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from PIL import Image

logger = logging.getLogger(__name__)


class MediaProcessor:
    """Process images and videos for Instagram specifications."""
    
    # Instagram specifications (updated 2025)
    MAX_IMAGE_SIZE = 1080  # pixels
    MAX_VIDEO_DURATION = 180  # seconds for Reels/Feed (3 minutes)
    MAX_STORY_DURATION = 60  # seconds for Stories
    STORY_ASPECT_RATIO = (9, 16)  # 9:16 for stories
    FEED_ASPECT_RATIO = (4, 5)  # 4:5 for feed posts (industry standard)
    LANDSCAPE_ASPECT_RATIO = (16, 9)  # 16:9 for landscape feed posts
    IMAGE_QUALITY = 85  # JPEG quality (0-100)
    
    # Official Instagram aspect ratios
    INSTAGRAM_RATIOS = {
        'feed': [(4, 5), (1, 1), (1.91, 1)],  # 4:5, 1:1, 1.91:1
        'reels': [(9, 16)],  # 9:16 only
        'stories': [(9, 16)],  # 9:16 only
        'carousel': [(4, 5), (1, 1)],  # 4:5, 1:1 (all slides must match)
    }
    
    @staticmethod
    def process_image(
        image_path: str,
        target_aspect: tuple[int, int] = (4, 5),
        max_size: int = MAX_IMAGE_SIZE
    ) -> str:
        """Process image for Instagram (resize, compress, format).
        
        Args:
            image_path: Path to image file
            target_aspect: Target aspect ratio (width, height)
            max_size: Maximum dimension in pixels
            
        Returns:
            Path to processed image file
            
        Raises:
            Exception: If image processing fails
        """
        try:
            img = Image.open(image_path)
            
            # Convert to RGB if necessary (for JPEG output)
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            
            # Resize to target aspect ratio
            img = MediaProcessor._resize_to_aspect(img, target_aspect)
            
            # Compress to max dimensions
            img = MediaProcessor._compress_image(img, max_size)
            
            # Save to temp file
            temp_path = MediaProcessor._save_temp_image(img)
            logger.info(f"Processed image: {image_path} -> {temp_path}")
            return temp_path
            
        except Exception as e:
            logger.error(f"Image processing failed: {e}")
            raise
    
    @staticmethod
    def process_image_smart(
        image_path: str,
        media_type: str = "feed",
        fit_mode: str = "auto"
    ) -> str:
        """Process image with smart aspect ratio handling.
        
        Args:
            image_path: Path to image file
            media_type: Type of media ("feed", "reels", "stories", "carousel")
            fit_mode: "auto" (auto-detect best approach), "fit" (letterbox, no crop), "crop" (crop to fit)
            
        Returns:
            Path to processed image file
            
        Raises:
            Exception: If image processing fails
        """
        try:
            img = Image.open(image_path)
            width, height = img.size
            
            # Convert to RGB if necessary
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            
            # Find closest valid aspect ratio
            target_aspect = MediaProcessor._find_closest_aspect_ratio(width, height, media_type)
            
            # Determine processing approach based on fit_mode
            if fit_mode == "auto":
                # Stories/Reels always use fit mode (no cropping) for aesthetic reasons
                if media_type in ["stories", "reels"]:
                    img = MediaProcessor._fit_to_aspect_ratio(img, target_aspect)
                else:
                    # Feed/carousel use crop for cleaner aesthetic
                    img = MediaProcessor._resize_to_aspect(img, target_aspect)
            elif fit_mode == "fit":
                # Always use letterbox/pillarbox (no cropping)
                img = MediaProcessor._fit_to_aspect_ratio(img, target_aspect)
            elif fit_mode == "crop":
                # Always crop to fit
                img = MediaProcessor._resize_to_aspect(img, target_aspect)
            
            # Compress to max dimensions
            img = MediaProcessor._compress_image(img, MediaProcessor.MAX_IMAGE_SIZE)
            
            # Save to temp file
            temp_path = MediaProcessor._save_temp_image(img)
            logger.info(f"Smart processed image: {image_path} -> {temp_path} (ratio: {target_aspect}, mode: {fit_mode})")
            return temp_path
            
        except Exception as e:
            logger.error(f"Smart image processing failed: {e}")
            raise
    
    @staticmethod
    def process_image_flexible(
        image_path: str,
        target_aspect: tuple[int, int] | None = None,
        max_size: int = MAX_IMAGE_SIZE,
        force_aspect: bool = False
    ) -> str:
        """Process image with flexible aspect ratio handling.
        
        Args:
            image_path: Path to image file
            target_aspect: Target aspect ratio (width, height). If None, preserves original
            max_size: Maximum dimension in pixels
            force_aspect: If True, force conversion to target aspect ratio
            
        Returns:
            Path to processed image file
            
        Raises:
            Exception: If image processing fails
        """
        try:
            img = Image.open(image_path)
            
            # Convert to RGB if necessary (for JPEG output)
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            
            # Only force aspect ratio if specified
            if target_aspect and force_aspect:
                img = MediaProcessor._resize_to_aspect(img, target_aspect)
            
            # Compress to max dimensions
            img = MediaProcessor._compress_image(img, max_size)
            
            # Save to temp file
            temp_path = MediaProcessor._save_temp_image(img)
            logger.info(f"Processed image with flexible aspect: {image_path} -> {temp_path}")
            return temp_path
            
        except Exception as e:
            logger.error(f"Image processing failed: {e}")
            raise
    
    @staticmethod
    def _find_closest_aspect_ratio(
        width: int,
        height: int,
        media_type: str = "feed"
    ) -> tuple[int, int]:
        """Find the closest valid Instagram aspect ratio for the given dimensions.
        
        Args:
            width: Source image width
            height: Source image height
            media_type: Type of media ("feed", "reels", "stories", "carousel")
            
        Returns:
            Closest valid aspect ratio as (width, height) tuple
        """
        if height == 0:
            return (4, 5)  # Default to 4:5 if invalid
        
        source_ratio = width / height
        valid_ratios = MediaProcessor.INSTAGRAM_RATIOS.get(media_type, [(4, 5), (1, 1)])
        
        # Find closest ratio
        closest_ratio = min(valid_ratios, key=lambda r: abs((r[0] / r[1]) - source_ratio))
        return closest_ratio
    
    @staticmethod
    def _fit_to_aspect_ratio(
        img: Image.Image,
        target_aspect: tuple[int, int],
        background_color: tuple[int, int, int] = (0, 0, 0)
    ) -> Image.Image:
        """Fit image to target aspect ratio using letterbox/pillarbox (no cropping).
        
        Args:
            img: PIL Image
            target_aspect: Target aspect ratio (width, height)
            background_color: RGB color for padding (default black)
            
        Returns:
            Fitted PIL Image with padding
        """
        width, height = img.size
        target_width, target_height = target_aspect
        target_ratio = target_width / target_height
        current_ratio = width / height
        
        # Calculate new dimensions to fit within target aspect ratio
        if current_ratio > target_ratio:
            # Image is wider than target - fit to width, pad height
            new_width = width
            new_height = int(width / target_ratio)
        else:
            # Image is taller than target - fit to height, pad width
            new_height = height
            new_width = int(height * target_ratio)
        
        # Resize image to fit target aspect ratio
        img_resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Create canvas with target dimensions
        canvas_width = max(new_width, int(max(new_width, new_height) * target_ratio))
        canvas_height = max(new_height, int(max(new_width, new_height) / target_ratio))
        
        # Create background canvas
        canvas = Image.new('RGB', (canvas_width, canvas_height), background_color)
        
        # Center the resized image on canvas
        paste_x = (canvas_width - new_width) // 2
        paste_y = (canvas_height - new_height) // 2
        canvas.paste(img_resized, (paste_x, paste_y))
        
        return canvas
    
    @staticmethod
    def _resize_to_aspect(
        img: Image.Image,
        target_aspect: tuple[int, int]
    ) -> Image.Image:
        """Resize image to target aspect ratio with center crop.
        
        Args:
            img: PIL Image
            target_aspect: Target aspect ratio (width, height)
            
        Returns:
            Resized PIL Image
        """
        width, height = img.size
        target_width, target_height = target_aspect
        
        # Calculate current aspect ratio
        current_aspect = width / height
        target_aspect_ratio = target_width / target_height
        
        if current_aspect > target_aspect_ratio:
            # Image is wider than target - crop width
            new_width = int(height * target_aspect_ratio)
            left = (width - new_width) // 2
            right = left + new_width
            img = img.crop((left, 0, right, height))
        elif current_aspect < target_aspect_ratio:
            # Image is taller than target - crop height
            new_height = int(width / target_aspect_ratio)
            top = (height - new_height) // 2
            bottom = top + new_height
            img = img.crop((0, top, width, bottom))
        
        return img
    
    @staticmethod
    def _compress_image(
        img: Image.Image,
        max_size: int
    ) -> Image.Image:
        """Compress image to max dimensions.
        
        Args:
            img: PIL Image
            max_size: Maximum dimension in pixels
            
        Returns:
            Compressed PIL Image
        """
        width, height = img.size
        
        if max(width, height) > max_size:
            if width > height:
                new_width = max_size
                new_height = int(height * (max_size / width))
            else:
                new_height = max_size
                new_width = int(width * (max_size / height))
            
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        return img
    
    @staticmethod
    def _save_temp_image(img: Image.Image) -> str:
        """Save image to temporary file.
        
        Args:
            img: PIL Image
            
        Returns:
            Path to temporary file
        """
        temp_dir = Path(tempfile.gettempdir()) / "instagram-media"
        temp_dir.mkdir(exist_ok=True)
        
        temp_path = temp_dir / f"processed_{Path(tempfile.gettempdir()).name}.jpg"
        img.save(temp_path, 'JPEG', quality=MediaProcessor.IMAGE_QUALITY, optimize=True)
        
        return str(temp_path)
    
    @staticmethod
    def validate_image(image_path: str) -> bool:
        """Validate image meets Instagram requirements.
        
        Args:
            image_path: Path to image file
            
        Returns:
            True if valid, False otherwise
        """
        try:
            img = Image.open(image_path)
            
            # Check format
            if img.format not in ['JPEG', 'PNG', 'JPG']:
                return False
            
            # Check size
            if max(img.size) > MediaProcessor.MAX_IMAGE_SIZE:
                return False
            
            return True
        except Exception:
            return False
    
    @staticmethod
    def process_video_smart(
        video_path: str,
        media_type: str = "feed",
        max_duration: int | None = None
    ) -> tuple[str, str]:
        """Process video with smart aspect ratio handling.
        
        Args:
            video_path: Path to video file
            media_type: Type of media ("feed", "reels", "stories")
            max_duration: Custom max duration (overrides defaults)
            
        Returns:
            Tuple of (processed_video_path, thumbnail_path)
            
        Raises:
            Exception: If video processing fails
        """
        try:
            # Try to import moviepy
            from moviepy.editor import VideoFileClip
        except ImportError:
            raise NotImplementedError(
                "Video processing requires moviepy dependency. "
                "Install with: uv sync"
            )
        
        try:
            video = VideoFileClip(video_path)
            width, height = video.size
            
            # Use provided max_duration or defaults
            if max_duration is None:
                max_duration = MediaProcessor.MAX_STORY_DURATION if media_type == "stories" else MediaProcessor.MAX_VIDEO_DURATION
            
            # Check duration
            if video.duration > max_duration:
                logger.warning(f"Video duration {video.duration}s exceeds limit {max_duration}s, trimming")
                video = video.subclip(0, max_duration)
            else:
                logger.info(f"Video duration {video.duration}s within limit {max_duration}s")
            
            # Smart aspect ratio handling for videos
            if media_type in ["reels", "stories"]:
                # Reels and stories must be 9:16 - use fit mode (letterbox) to preserve content
                target_aspect = (9, 16)
                current_ratio = width / height
                target_ratio = target_aspect[0] / target_aspect[1]
                
                if abs(current_ratio - target_ratio) > 0.1:  # If significantly different from 9:16
                    logger.info(f"Video aspect ratio {width}x{height} differs from 9:16, applying letterbox")
                    # Fit to 9:16 with letterbox (no cropping)
                    # This requires creating a 9:16 canvas and placing the video
                    video = MediaProcessor._fit_video_to_aspect(video, target_aspect)
            elif media_type == "feed":
                # Feed videos can be 4:5, 1:1, or 16:9 - find closest valid ratio
                target_aspect = MediaProcessor._find_closest_aspect_ratio(width, height, "feed")
                target_ratio = target_aspect[0] / target_aspect[1]
                current_ratio = width / height
                
                if abs(current_ratio - target_ratio) > 0.1:  # If significantly different
                    logger.info(f"Video aspect ratio {width}x{height} differs from target {target_aspect}, applying letterbox")
                    video = MediaProcessor._fit_video_to_aspect(video, target_aspect)
            
            # Generate thumbnail
            thumbnail_dir = Path(tempfile.gettempdir()) / "instagram-media"
            thumbnail_dir.mkdir(exist_ok=True)
            thumbnail_path = thumbnail_dir / f"thumbnail_{Path(video_path).stem}.jpg"
            video.save_frame(str(thumbnail_path), t=0.5)  # Save frame at 0.5 seconds
            
            # Compress video
            temp_dir = Path(tempfile.gettempdir()) / "instagram-media"
            temp_dir.mkdir(exist_ok=True)
            processed_path = temp_dir / f"processed_{Path(video_path).stem}.mp4"
            
            # Write with optimized settings
            video.write_videofile(
                str(processed_path),
                codec='libx264',
                audio_codec='aac',
                bitrate='8000k',
                threads=4,
                logger=None  # Suppress moviepy logging
            )
            
            video.close()
            
            logger.info(f"Smart processed video: {video_path} -> {processed_path} (media_type: {media_type})")
            return str(processed_path), str(thumbnail_path)
            
        except Exception as e:
            logger.error(f"Smart video processing failed: {e}")
            raise
    
    @staticmethod
    def _fit_video_to_aspect(
        video: VideoFileClip,
        target_aspect: tuple[int, int]
    ) -> VideoFileClip:
        """Fit video to target aspect ratio using letterbox/pillarbox (no cropping).
        
        Args:
            video: MoviePy VideoFileClip
            target_aspect: Target aspect ratio (width, height)
            
        Returns:
            Fitted VideoFileClip with padding
        """
        width, height = video.size
        target_width, target_height = target_aspect
        target_ratio = target_width / target_height
        current_ratio = width / height
        
        # Calculate new dimensions to fit within target aspect ratio
        if current_ratio > target_ratio:
            # Video is wider than target - fit to width, pad height
            new_width = width
            new_height = int(width / target_ratio)
        else:
            # Video is taller than target - fit to height, pad width
            new_height = height
            new_width = int(height * target_ratio)
        
        # Resize video to fit target aspect ratio
        video_resized = video.resize((new_width, new_height))
        
        # Create black background
        canvas_width = max(new_width, int(max(new_width, new_height) * target_ratio))
        canvas_height = max(new_height, int(max(new_width, new_height) / target_ratio))
        
        # Composite video onto black canvas
        from moviepy.editor import ColorClip, CompositeVideoClip
        black_canvas = ColorClip(size=(canvas_width, canvas_height), color=(0, 0, 0), duration=video.duration)
        
        # Center the video on canvas
        video_final = CompositeVideoClip([black_canvas, video_resized.set_position((canvas_width - new_width) // 2, (canvas_height - new_height) // 2)])
        
        return video_final
    
    @staticmethod
    def process_video(
        video_path: str,
        is_story: bool = False,
        max_duration: int | None = None
    ) -> tuple[str, str]:
        """Process video for Instagram (compress, generate thumbnail).
        
        Args:
            video_path: Path to video file
            is_story: Whether this is for a story (affects duration limits)
            max_duration: Custom max duration (overrides defaults)
            
        Returns:
            Tuple of (processed_video_path, thumbnail_path)
            
        Raises:
            Exception: If video processing fails
        """
        try:
            # Try to import moviepy
            from moviepy.editor import VideoFileClip
        except ImportError:
            raise NotImplementedError(
                "Video processing requires moviepy dependency. "
                "Install with: uv sync"
            )
        
        try:
            video = VideoFileClip(video_path)
            
            # Use provided max_duration or defaults
            if max_duration is None:
                max_duration = MediaProcessor.MAX_STORY_DURATION if is_story else MediaProcessor.MAX_VIDEO_DURATION
            
            # Check duration
            if video.duration > max_duration:
                logger.warning(f"Video duration {video.duration}s exceeds limit {max_duration}s, trimming")
                video = video.subclip(0, max_duration)
            else:
                logger.info(f"Video duration {video.duration}s within limit {max_duration}s")
            
            # Generate thumbnail
            thumbnail_dir = Path(tempfile.gettempdir()) / "instagram-media"
            thumbnail_dir.mkdir(exist_ok=True)
            thumbnail_path = thumbnail_dir / f"thumbnail_{Path(video_path).stem}.jpg"
            video.save_frame(str(thumbnail_path), t=0.5)  # Save frame at 0.5 seconds
            
            # Compress video
            temp_dir = Path(tempfile.gettempdir()) / "instagram-media"
            temp_dir.mkdir(exist_ok=True)
            processed_path = temp_dir / f"processed_{Path(video_path).stem}.mp4"
            
            # Write with optimized settings
            video.write_videofile(
                str(processed_path),
                codec='libx264',
                audio_codec='aac',
                bitrate='8000k',
                threads=4,
                logger=None  # Suppress moviepy logging
            )
            
            video.close()
            
            logger.info(f"Processed video: {video_path} -> {processed_path}")
            return str(processed_path), str(thumbnail_path)
            
        except Exception as e:
            logger.error(f"Video processing failed: {e}")
            raise
    
    @staticmethod
    def validate_video(video_path: str, is_story: bool = False) -> bool:
        """Validate video meets Instagram requirements.
        
        Args:
            video_path: Path to video file
            is_story: Whether this is for a story
            
        Returns:
            True if valid, False otherwise
        """
        # Video validation will be implemented in Phase 2
        # For now, just check file extension
        path = Path(video_path)
        return path.suffix.lower() in ['.mp4', '.mov', '.avi']