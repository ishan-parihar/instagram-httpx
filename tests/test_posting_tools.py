"""
Tests for content posting tools functionality.
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, timezone, timedelta

from instagram_mcp_server.posting.validators import PostingValidator
from instagram_mcp_server.posting.media_processor import MediaProcessor
from instagram_mcp_server.posting.client import PostingClient, handle_instagrapi_error
from instagram_mcp_server.multi_account import (
    AccountMetadata,
    check_account_posting_limits,
    get_active_account,
    record_post_attempt,
)


@pytest.fixture
def sample_account():
    """Create a sample account for testing."""
    return AccountMetadata(
        account_id="test_account",
        username="testuser",
        posting_enabled=True,
        daily_post_limit=10,
        last_post_time=None,
        post_count_today=0,
        last_reset_date=datetime.now(timezone.utc).isoformat(),
    )


@pytest.fixture
def mock_context():
    """Mock FastMCP Context."""
    ctx = MagicMock()
    ctx.report_progress = AsyncMock()
    return ctx


@pytest.fixture
def mock_instagrapi_client():
    """Mock instagrapi Client."""
    client = MagicMock()
    
    # Mock media objects
    mock_media = MagicMock()
    mock_media.pk = 123456789
    mock_media.code = "ABC123"
    mock_media.taken_at = datetime.now(timezone.utc)
    
    client.photo_upload = MagicMock(return_value=mock_media)
    client.video_upload = MagicMock(return_value=mock_media)
    client.album_upload = MagicMock(return_value=mock_media)
    client.photo_upload_to_story = MagicMock(return_value=mock_media)
    client.video_upload_to_story = MagicMock(return_value=mock_media)
    client.clip_upload = MagicMock(return_value=mock_media)
    client.login_by_sessionid = MagicMock()
    
    return client


class TestPostingValidators:
    """Test posting validation logic."""

    def test_validate_photo_path_valid_jpg(self, tmp_path):
        """Test validation of valid JPG photo path."""
        # Create a test JPG file
        test_file = tmp_path / "test.jpg"
        test_file.write_bytes(b"fake_jpg_data")
        
        valid, msg = PostingValidator.validate_photo_path(str(test_file))
        assert valid is True
        assert msg == ""

    def test_validate_photo_path_valid_png(self, tmp_path):
        """Test validation of valid PNG photo path."""
        # Create a test PNG file
        test_file = tmp_path / "test.png"
        test_file.write_bytes(b"fake_png_data")
        
        valid, msg = PostingValidator.validate_photo_path(str(test_file))
        assert valid is True
        assert msg == ""

    def test_validate_photo_path_invalid_format(self, tmp_path):
        """Test validation of invalid photo format."""
        # Create a test file with invalid extension
        test_file = tmp_path / "test.gif"
        test_file.write_bytes(b"fake_gif_data")
        
        valid, msg = PostingValidator.validate_photo_path(str(test_file))
        assert valid is False
        assert "format" in msg.lower()

    def test_validate_photo_path_nonexistent(self):
        """Test validation of non-existent file."""
        valid, msg = PostingValidator.validate_photo_path("/nonexistent/file.jpg")
        assert valid is False
        assert "not found" in msg.lower() or "does not exist" in msg.lower()

    def test_validate_caption_valid(self):
        """Test validation of valid caption."""
        caption = "This is a valid caption"
        valid, msg = PostingValidator.validate_caption(caption)
        assert valid is True
        assert msg == ""

    def test_validate_caption_empty(self):
        """Test validation of empty caption."""
        caption = ""
        valid, msg = PostingValidator.validate_caption(caption)
        assert valid is False  # Empty captions are not allowed
        assert "empty" in msg.lower()

    def test_validate_caption_too_long(self):
        """Test validation of caption exceeding limit."""
        caption = "x" * 2300  # Exceeds 2200 character limit
        valid, msg = PostingValidator.validate_caption(caption)
        assert valid is False
        assert "too long" in msg.lower() or "exceeds" in msg.lower()

    def test_validate_caption_at_limit(self):
        """Test validation of caption at exact limit."""
        caption = "x" * 2200  # Exactly at limit
        valid, msg = PostingValidator.validate_caption(caption)
        assert valid is True
        assert msg == ""

    def test_validate_video_path_valid_mp4(self, tmp_path):
        """Test validation of valid MP4 video path."""
        # Create a test MP4 file
        test_file = tmp_path / "test.mp4"
        test_file.write_bytes(b"fake_mp4_data")
        
        valid, msg = PostingValidator.validate_video_path(str(test_file))
        assert valid is True
        assert msg == ""

    def test_validate_video_path_valid_mov(self, tmp_path):
        """Test validation of valid MOV video path."""
        # Create a test MOV file
        test_file = tmp_path / "test.mov"
        test_file.write_bytes(b"fake_mov_data")
        
        valid, msg = PostingValidator.validate_video_path(str(test_file))
        assert valid is True
        assert msg == ""

    def test_validate_video_path_invalid_format(self, tmp_path):
        """Test validation of invalid video format."""
        # Create a test file with invalid extension
        test_file = tmp_path / "test.wmv"
        test_file.write_bytes(b"fake_wmv_data")
        
        valid, msg = PostingValidator.validate_video_path(str(test_file))
        assert valid is False
        assert "format" in msg.lower()

    def test_validate_aspect_ratio_feed_4_5(self):
        """Test validation of 4:5 aspect ratio for feed."""
        valid, msg = PostingValidator.validate_aspect_ratio(1080, 1350, "feed")
        assert valid is True
        assert msg == ""

    def test_validate_aspect_ratio_feed_1_1(self):
        """Test validation of 1:1 aspect ratio for feed."""
        valid, msg = PostingValidator.validate_aspect_ratio(1080, 1080, "feed")
        assert valid is True
        assert msg == ""

    def test_validate_aspect_ratio_feed_1_91_1(self):
        """Test validation of 1.91:1 aspect ratio for feed."""
        valid, msg = PostingValidator.validate_aspect_ratio(1080, 566, "feed")
        assert valid is True
        assert msg == ""

    def test_validate_aspect_ratio_feed_16_9_valid(self):
        """Test validation of 16:9 aspect ratio for feed (should be valid)."""
        valid, msg = PostingValidator.validate_aspect_ratio(1920, 1080, "feed")
        assert valid is True
        assert msg == ""

    def test_validate_aspect_ratio_feed_invalid(self):
        """Test validation of invalid aspect ratio for feed (too wide)."""
        valid, msg = PostingValidator.validate_aspect_ratio(2000, 1000, "feed")  # 2:1 ratio
        assert valid is False
        assert "Invalid aspect ratio" in msg

    def test_validate_aspect_ratio_reels_9_16(self):
        """Test validation of 9:16 aspect ratio for reels."""
        valid, msg = PostingValidator.validate_aspect_ratio(1080, 1920, "reels")
        assert valid is True
        assert msg == ""

    def test_validate_aspect_ratio_reels_invalid(self):
        """Test validation of invalid aspect ratio for reels."""
        valid, msg = PostingValidator.validate_aspect_ratio(1080, 1080, "reels")
        assert valid is False
        assert "Invalid aspect ratio" in msg

    def test_validate_aspect_ratio_stories_9_16(self):
        """Test validation of 9:16 aspect ratio for stories."""
        valid, msg = PostingValidator.validate_aspect_ratio(1080, 1920, "stories")
        assert valid is True
        assert msg == ""

    def test_validate_aspect_ratio_stories_invalid(self):
        """Test validation of invalid aspect ratio for stories."""
        valid, msg = PostingValidator.validate_aspect_ratio(1080, 1350, "stories")
        assert valid is False
        assert "Invalid aspect ratio" in msg

    def test_validate_aspect_ratio_carousel_4_5(self):
        """Test validation of 4:5 aspect ratio for carousel."""
        valid, msg = PostingValidator.validate_aspect_ratio(1080, 1350, "carousel")
        assert valid is True
        assert msg == ""

    def test_validate_aspect_ratio_carousel_1_1(self):
        """Test validation of 1:1 aspect ratio for carousel."""
        valid, msg = PostingValidator.validate_aspect_ratio(1080, 1080, "carousel")
        assert valid is True
        assert msg == ""

    def test_validate_aspect_ratio_carousel_invalid(self):
        """Test validation of invalid aspect ratio for carousel."""
        valid, msg = PostingValidator.validate_aspect_ratio(1080, 1920, "carousel")
        assert valid is False
        assert "Invalid aspect ratio" in msg

    def test_validate_carousel_paths_valid(self, tmp_path):
        """Test validation of valid carousel paths."""
        # Create test image files
        file1 = tmp_path / "test1.jpg"
        file2 = tmp_path / "test2.jpg"
        file1.write_bytes(b"fake_jpg_1")
        file2.write_bytes(b"fake_jpg_2")
        
        valid, msg = PostingValidator.validate_carousel_paths([str(file1), str(file2)])
        assert valid is True
        assert msg == ""

    def test_validate_carousel_paths_too_few(self, tmp_path):
        """Test validation of carousel with too few items."""
        file1 = tmp_path / "test1.jpg"
        file1.write_bytes(b"fake_jpg_1")
        
        valid, msg = PostingValidator.validate_carousel_paths([str(file1)])
        assert valid is False
        assert "at least 2" in msg.lower() or "minimum" in msg.lower()

    def test_validate_carousel_paths_too_many(self, tmp_path):
        """Test validation of carousel with too many items."""
        paths = []
        for i in range(11):
            file = tmp_path / f"test{i}.jpg"
            file.write_bytes(b"fake_jpg")
            paths.append(str(file))
        
        valid, msg = PostingValidator.validate_carousel_paths(paths)
        assert valid is False
        assert "at most 10" in msg.lower() or "maximum" in msg.lower()

    def test_validate_carousel_paths_mixed_formats(self, tmp_path):
        """Test validation of carousel with mixed valid formats."""
        file1 = tmp_path / "test1.jpg"
        file2 = tmp_path / "test2.png"
        file1.write_bytes(b"fake_jpg")
        file2.write_bytes(b"fake_png")
        
        valid, msg = PostingValidator.validate_carousel_paths([str(file1), str(file2)])
        assert valid is True
        assert msg == ""


class TestMediaProcessor:
    """Test media processing functionality."""

    def test_process_image_nonexistent_file(self):
        """Test image processing with non-existent file."""
        with pytest.raises(Exception):
            MediaProcessor.process_image("/nonexistent/file.jpg")

    def test_process_video_nonexistent_file(self):
        """Test video processing with non-existent file."""
        with pytest.raises(Exception):
            MediaProcessor.process_video("/nonexistent/file.mp4")


class TestPostingClient:
    """Test posting client functionality."""

    def test_client_initialization_no_active_account(self):
        """Test client initialization when no active account exists."""
        with patch('instagram_mcp_server.posting.client.get_active_account') as mock_get_active:
            mock_get_active.return_value = None
            
            with pytest.raises(Exception):  # Should raise AuthenticationError
                PostingClient()


class TestErrorHandling:
    """Test error handling for posting operations."""

    def test_handle_instagrapi_challenge_required(self):
        """Test handling of ChallengeRequired error."""
        from instagrapi.exceptions import ChallengeRequired
        
        error = ChallengeRequired("Challenge required")
        success, message = handle_instagrapi_error(error)
        
        assert success is False
        assert "challenge" in message.lower()

    def test_handle_instagrapi_login_required(self):
        """Test handling of LoginRequired error."""
        from instagrapi.exceptions import LoginRequired
        
        error = LoginRequired("Login required")
        success, message = handle_instagrapi_error(error)
        
        assert success is False
        assert "login" in message.lower() or "session" in message.lower()

    def test_handle_instagrapi_feedback_required(self):
        """Test handling of FeedbackRequired error."""
        from instagrapi.exceptions import FeedbackRequired
        
        error = FeedbackRequired("Feedback required")
        success, message = handle_instagrapi_error(error)
        
        assert success is False
        assert "feedback" in message.lower()

    def test_handle_instagrapi_sentry_block(self):
        """Test handling of SentryBlock error."""
        from instagrapi.exceptions import SentryBlock
        
        error = SentryBlock("Sentry block")
        success, message = handle_instagrapi_error(error)
        
        assert success is False
        assert "block" in message.lower()

    def test_handle_generic_error(self):
        """Test handling of generic error."""
        error = Exception("Generic error")
        success, message = handle_instagrapi_error(error)
        
        assert success is False
        assert "unknown" in message.lower() or "generic" in message.lower()


class TestAccountLimits:
    """Test account posting limits functionality."""

    def test_check_account_posting_limits_under_limit(self, sample_account):
        """Test posting limits when under daily limit."""
        sample_account.post_count_today = 5
        sample_account.last_post_time = (datetime.now(timezone.utc) - timedelta(minutes=60)).isoformat()
        
        with patch('instagram_mcp_server.multi_account.get_account') as mock_get:
            mock_get.return_value = sample_account
            
            can_post, reason = check_account_posting_limits("test_account")
            
            assert can_post is True
            assert reason == ""

    def test_check_account_posting_limits_at_limit(self, sample_account):
        """Test posting limits when at daily limit."""
        sample_account.post_count_today = 10  # At limit
        sample_account.last_post_time = (datetime.now(timezone.utc) - timedelta(minutes=60)).isoformat()
        
        with patch('instagram_mcp_server.multi_account.get_account') as mock_get:
            mock_get.return_value = sample_account
            
            can_post, reason = check_account_posting_limits("test_account")
            
            assert can_post is False
            assert "limit" in reason.lower()

    def test_check_account_posting_limits_in_cooldown(self, sample_account):
        """Test posting limits when in cooldown period."""
        sample_account.post_count_today = 1
        sample_account.last_post_time = (datetime.now(timezone.utc) - timedelta(minutes=15)).isoformat()  # In cooldown
        
        with patch('instagram_mcp_server.multi_account.get_account') as mock_get:
            mock_get.return_value = sample_account
            
            can_post, reason = check_account_posting_limits("test_account")
            
            assert can_post is False
            assert "cooldown" in reason.lower()

    def test_record_post_attempt_success(self, sample_account):
        """Test recording successful post attempt."""
        with patch('instagram_mcp_server.multi_account.get_account') as mock_get, \
             patch('instagram_mcp_server.multi_account.increment_account_post_count') as mock_increment:
            
            mock_get.return_value = sample_account
            
            record_post_attempt(
                account_id="test_account",
                media_type="photo",
                success=True,
                post_id="123456"
            )
            
            # Should call increment function
            mock_increment.assert_called_once_with("test_account")

    def test_record_post_attempt_failure(self, sample_account):
        """Test recording failed post attempt."""
        with patch('instagram_mcp_server.multi_account.get_account') as mock_get, \
             patch('instagram_mcp_server.multi_account.increment_account_post_count') as mock_increment:
            
            mock_get.return_value = sample_account
            
            record_post_attempt(
                account_id="test_account",
                media_type="photo",
                success=False,
                error_message="Upload failed"
            )
            
            # Should not call increment for failure
            mock_increment.assert_not_called()