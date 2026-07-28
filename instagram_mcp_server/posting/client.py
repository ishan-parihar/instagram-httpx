"""
Instagram posting client wrapper.

Wraps instagrapi Client with multi-account support and error handling.
"""

from __future__ import annotations

import logging
from typing import Any

from instagrapi import Client
from instagrapi.exceptions import (
    ChallengeRequired,
    LoginRequired,
    FeedbackRequired,
    SentryBlock,
)

from instagram_mcp_server.core.exceptions import AuthenticationError
from instagram_mcp_server.multi_account import get_account_cookies, get_active_account

logger = logging.getLogger(__name__)


class PostingClient:
    """Wrapper around instagrapi with multi-account support."""
    
    def __init__(self, account_id: str | None = None):
        """Initialize posting client with account-specific cookies.
        
        Args:
            account_id: Optional account ID to use for posting. If not provided,
                      uses the active account.
        
        Raises:
            AuthenticationError: If account not found or no cookies available
        """
        self.account_id = account_id
        self.cookies = self._get_cookies()
        self.client = self._create_client()
        
        logger.info(
            f"PostingClient initialized for account: {self.account_id or 'active'}"
        )
    
    def _get_cookies(self) -> dict[str, str]:
        """Get cookies for account (with fallback to active account).
        
        Returns:
            Dictionary of Instagram cookies
            
        Raises:
            AuthenticationError: If account not found or no cookies available
        """
        if self.account_id:
            cookies = get_account_cookies(self.account_id)
            if not cookies:
                raise AuthenticationError(f"Account {self.account_id} not found or no cookies")
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
        """Create instagrapi client with account cookies.
        
        Returns:
            Configured instagrapi Client instance
        """
        client = Client()
        
        # Check if we have a sessionid
        if "sessionid" in self.cookies:
            sessionid = self.cookies["sessionid"]
            try:
                # Use login_by_sessionid to authenticate with existing session
                client.login_by_sessionid(sessionid)
                logger.info(f"Authenticated with sessionid for account: {self.account_id or 'active'}")
            except Exception as e:
                logger.warning(f"Failed to login with sessionid: {e}")
                # Fall back to setting cookies manually if possible
                try:
                    # Set sessionid as a fallback
                    setattr(client, 'sessionid', sessionid)
                except Exception:
                    pass
        else:
            logger.warning("No sessionid found in cookies")
        
        return client
    
    def upload_photo(
        self,
        path: str,
        caption: str,
        **kwargs: Any,
    ) -> Any:
        """Upload photo using instagrapi.
        
        Args:
            path: Path to image file
            caption: Photo caption
            **kwargs: Additional instagrapi photo_upload parameters
        
        Returns:
            Media object from instagrapi
        
        Raises:
            AuthenticationError: If session is invalid
            Exception: For other Instagram API errors
        """
        from pathlib import Path
        
        try:
            return self.client.photo_upload(Path(path), caption, **kwargs)
        except (ChallengeRequired, LoginRequired) as e:
            logger.error(f"Authentication error: {e}")
            raise AuthenticationError(f"Session invalid: {str(e)}")
        except Exception as e:
            logger.error(f"Photo upload error: {e}")
            raise
    
    def upload_video(
        self,
        path: str,
        caption: str,
        **kwargs: Any,
    ) -> Any:
        """Upload video using instagrapi.
        
        Args:
            path: Path to video file
            caption: Video caption
            **kwargs: Additional instagrapi video_upload parameters
        
        Returns:
            Media object from instagrapi
        
        Raises:
            AuthenticationError: If session is invalid
            Exception: For other Instagram API errors
        """
        from pathlib import Path
        
        try:
            return self.client.video_upload(Path(path), caption, **kwargs)
        except (ChallengeRequired, LoginRequired) as e:
            logger.error(f"Authentication error: {e}")
            raise AuthenticationError(f"Session invalid: {str(e)}")
        except Exception as e:
            logger.error(f"Video upload error: {e}")
            raise
    
    def upload_carousel(
        self,
        paths: list[str],
        caption: str,
        **kwargs: Any,
    ) -> Any:
        """Upload carousel using instagrapi.
        
        Args:
            paths: List of paths to media files
            caption: Carousel caption
            **kwargs: Additional instagrapi album_upload parameters
        
        Returns:
            Media object from instagrapi
        
        Raises:
            AuthenticationError: If session is invalid
            Exception: For other Instagram API errors
        """
        from pathlib import Path
        
        try:
            return self.client.album_upload([Path(p) for p in paths], caption, **kwargs)
        except (ChallengeRequired, LoginRequired) as e:
            logger.error(f"Authentication error: {e}")
            raise AuthenticationError(f"Session invalid: {str(e)}")
        except Exception as e:
            logger.error(f"Carousel upload error: {e}")
            raise
    
    def upload_story_photo(
        self,
        path: str,
        **kwargs: Any,
    ) -> Any:
        """Upload photo story using instagrapi.
        
        Args:
            path: Path to image file
            **kwargs: Additional instagrapi photo_upload_to_story parameters
        
        Returns:
            Story object from instagrapi
        
        Raises:
            AuthenticationError: If session is invalid
            Exception: For other Instagram API errors
        """
        from pathlib import Path
        
        try:
            return self.client.photo_upload_to_story(Path(path), **kwargs)
        except (ChallengeRequired, LoginRequired) as e:
            logger.error(f"Authentication error: {e}")
            raise AuthenticationError(f"Session invalid: {str(e)}")
        except Exception as e:
            logger.error(f"Story photo upload error: {e}")
            raise
    
    def upload_story_video(
        self,
        path: str,
        **kwargs: Any,
    ) -> Any:
        """Upload video story using instagrapi.
        
        Args:
            path: Path to video file
            **kwargs: Additional instagrapi video_upload_to_story parameters
        
        Returns:
            Story object from instagrapi
        
        Raises:
            AuthenticationError: If session is invalid
            Exception: For other Instagram API errors
        """
        from pathlib import Path
        
        try:
            return self.client.video_upload_to_story(Path(path), **kwargs)
        except (ChallengeRequired, LoginRequired) as e:
            logger.error(f"Authentication error: {e}")
            raise AuthenticationError(f"Session invalid: {str(e)}")
        except Exception as e:
            logger.error(f"Story video upload error: {e}")
            raise
    
    def upload_reel(
        self,
        path: str,
        caption: str,
        **kwargs: Any,
    ) -> Any:
        """Upload reel using instagrapi.
        
        Args:
            path: Path to video file
            caption: Reel caption
            **kwargs: Additional instagrapi clip_upload parameters
        
        Returns:
            Media object from instagrapi
        
        Raises:
            AuthenticationError: If session is invalid
            Exception: For other Instagram API errors
        """
        from pathlib import Path
        
        try:
            return self.client.clip_upload(Path(path), caption, **kwargs)
        except (ChallengeRequired, LoginRequired) as e:
            logger.error(f"Authentication error: {e}")
            raise AuthenticationError(f"Session invalid: {str(e)}")
        except Exception as e:
            logger.error(f"Reel upload error: {e}")
            raise


def handle_instagrapi_error(error: Exception) -> tuple[bool, str]:
    """Handle instagrapi-specific errors.
    
    Args:
        error: Exception from instagrapi
        
    Returns:
        Tuple of (success, error_message)
    """
    if isinstance(error, ChallengeRequired):
        return False, "Challenge required - manual intervention needed"
    elif isinstance(error, LoginRequired):
        return False, "Login required - session expired, refresh cookies"
    elif isinstance(error, FeedbackRequired):
        return False, "Feedback required - account action needed"
    elif isinstance(error, SentryBlock):
        return False, "Sentry block - account temporarily blocked"
    else:
        return False, f"Unknown error: {str(error)}"