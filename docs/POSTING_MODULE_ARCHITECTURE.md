# Media Posting Module Architecture Design

## Module Structure

```
instagram_mcp_server/
├── posting/                                    # NEW: Media posting module
│   ├── __init__.py                           # Package initialization
│   ├── client.py                             # Instagrapi client wrapper
│   ├── media_processor.py                    # Image/video processing
│   ├── validators.py                         # Media validation
│   ├── templates.py                          # Post templates
│   ├── scheduler.py                         # Post scheduling
│   └── queue.py                             # Posting queue management
├── tools/
│   └── posting_tools.py                     # NEW: MCP posting tools
├── multi_account.py                          # EXISTING: Account management
├── dependencies.py                           # EXISTING: Client factory
└── scraping/
    └── api_client.py                        # EXISTING: Scraping client
```

## Component Design

### 1. Client Wrapper (`posting/client.py`)

**Purpose**: Wrap instagrapi Client with multi-account support and error handling

```python
from instagrapi import Client
from instagram_mcp_server.multi_account import get_account_cookies, get_active_account
from instagram_mcp_server.core.exceptions import AuthenticationError

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
    
    def upload_photo(self, path: str, caption: str, **kwargs):
        """Upload photo using instagrapi."""
        return self.client.photo_upload(path, caption, **kwargs)
    
    def upload_video(self, path: str, caption: str, **kwargs):
        """Upload video using instagrapi."""
        return self.client.video_upload(path, caption, **kwargs)
    
    def upload_carousel(self, paths: list[str], caption: str, **kwargs):
        """Upload carousel using instagrapi."""
        return self.client.album_upload(paths, caption, **kwargs)
    
    def upload_story_photo(self, path: str, **kwargs):
        """Upload photo story using instagrapi."""
        return self.client.photo_upload_to_story(path, **kwargs)
    
    def upload_story_video(self, path: str, **kwargs):
        """Upload video story using instagrapi."""
        return self.client.video_upload_to_story(path, **kwargs)
    
    def upload_reel(self, path: str, caption: str, **kwargs):
        """Upload reel using instagrapi."""
        return self.client.clip_upload(path, caption, **kwargs)
```

### 2. Media Processor (`posting/media_processor.py`)

**Purpose**: Handle image/video preprocessing for Instagram specifications

```python
from PIL import Image
from pathlib import Path
import tempfile
import logging

logger = logging.getLogger(__name__)

class MediaProcessor:
    """Process images and videos for Instagram specifications."""
    
    # Instagram specifications
    MAX_IMAGE_SIZE = 1080  # pixels
    MAX_VIDEO_DURATION = 60  # seconds for Reels
    MAX_STORY_DURATION = 15  # seconds for Stories
    STORY_ASPECT_RATIO = (9, 16)  # 9:16 for stories
    FEED_ASPECT_RATIO = (1, 1)  # 1:1 for feed posts
    
    @staticmethod
    def process_image(image_path: str, target_aspect: tuple = (1, 1)) -> str:
        """Process image for Instagram (resize, compress, format)."""
        img = Image.open(image_path)
        
        # Resize to target aspect ratio
        img = MediaProcessor._resize_to_aspect(img, target_aspect)
        
        # Compress to max dimensions
        img = MediaProcessor._compress_image(img)
        
        # Save to temp file
        temp_path = MediaProcessor._save_temp_image(img)
        return temp_path
    
    @staticmethod
    def process_video(video_path: str, is_story: bool = False) -> tuple[str, str]:
        """Process video for Instagram (compress, generate thumbnail)."""
        # Video processing with moviepy
        from moviepy.editor import VideoFileClip
        
        clip = VideoFileClip(video_path)
        
        # Check duration
        max_duration = MediaProcessor.MAX_STORY_DURATION if is_story else MediaProcessor.MAX_VIDEO_DURATION
        if clip.duration > max_duration:
            clip = clip.subclip(0, max_duration)
        
        # Resize to Instagram specifications
        target_aspect = MediaProcessor.STORY_ASPECT_RATIO if is_story else MediaProcessor.FEED_ASPECT_RATIO
        clip = MediaProcessor._resize_video_to_aspect(clip, target_aspect)
        
        # Save processed video
        temp_video = MediaProcessor._save_temp_video(clip)
        
        # Generate thumbnail
        temp_thumbnail = MediaProcessor._generate_thumbnail(clip)
        
        clip.close()
        return temp_video, temp_thumbnail
    
    @staticmethod
    def validate_image(image_path: str) -> bool:
        """Validate image meets Instagram requirements."""
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
    def validate_video(video_path: str, is_story: bool = False) -> bool:
        """Validate video meets Instagram requirements."""
        try:
            from moviepy.editor import VideoFileClip
            
            clip = VideoFileClip(video_path)
            
            # Check duration
            max_duration = MediaProcessor.MAX_STORY_DURATION if is_story else MediaProcessor.MAX_VIDEO_DURATION
            if clip.duration > max_duration:
                return False
            
            # Check format
            if video_path.lower().endswith('.mp4'):
                return True
            
            clip.close()
            return False
        except Exception:
            return False
```

### 3. Validators (`posting/validators.py`)

**Purpose**: Validate media and posting parameters

```python
from pathlib import Path
from typing import Any
import logging

logger = logging.getLogger(__name__)

class PostingValidator:
    """Validate posting parameters and media."""
    
    @staticmethod
    def validate_photo_path(image_path: str) -> tuple[bool, str]:
        """Validate photo path and file."""
        path = Path(image_path)
        
        if not path.exists():
            return False, f"Image file not found: {image_path}"
        
        if not path.is_file():
            return False, f"Path is not a file: {image_path}"
        
        # Check file extension
        valid_extensions = ['.jpg', '.jpeg', '.png']
        if path.suffix.lower() not in valid_extensions:
            return False, f"Invalid image format: {path.suffix}. Supported: {valid_extensions}"
        
        return True, ""
    
    @staticmethod
    def validate_video_path(video_path: str) -> tuple[bool, str]:
        """Validate video path and file."""
        path = Path(video_path)
        
        if not path.exists():
            return False, f"Video file not found: {video_path}"
        
        if not path.is_file():
            return False, f"Path is not a file: {video_path}"
        
        # Check file extension
        valid_extensions = ['.mp4', '.mov', '.avi']
        if path.suffix.lower() not in valid_extensions:
            return False, f"Invalid video format: {path.suffix}. Supported: {valid_extensions}"
        
        return True, ""
    
    @staticmethod
    def validate_caption(caption: str) -> tuple[bool, str]:
        """Validate caption text."""
        if not caption or not caption.strip():
            return False, "Caption cannot be empty"
        
        if len(caption) > 2200:  # Instagram caption limit
            return False, f"Caption too long: {len(caption)} characters (max 2200)"
        
        return True, ""
    
    @staticmethod
    def validate_carousel_paths(paths: list[str]) -> tuple[bool, str]:
        """Validate carousel media paths."""
        if len(paths) < 2 or len(paths) > 10:
            return False, f"Carousel must have 2-10 media items (got {len(paths)})"
        
        for path in paths:
            valid, msg = PostingValidator.validate_photo_path(path)
            if not valid:
                return False, f"Invalid carousel item: {msg}"
        
        return True, ""
```

### 4. Templates (`posting/templates.py`)

**Purpose**: Template-based posting system for consistent content

```python
from dataclasses import dataclass
from typing import Any
from pathlib import Path
import json
import logging

logger = logging.getLogger(__name__)

@dataclass
class PostTemplate:
    """Template for Instagram posts."""
    template_id: str
    name: str
    caption_template: str
    media_type: str  # "photo", "video", "carousel", "story"
    variables: list[str]
    default_hashtags: list[str]
    created_at: str

class TemplateManager:
    """Manage post templates."""
    
    def __init__(self):
        self.templates: dict[str, PostTemplate] = {}
        self._load_templates()
    
    def _load_templates(self):
        """Load templates from storage."""
        template_file = Path.home() / '.instagram-mcp' / 'templates.json'
        if template_file.exists():
            with open(template_file) as f:
                data = json.load(f)
                for template_data in data['templates']:
                    template = PostTemplate(**template_data)
                    self.templates[template.template_id] = template
    
    def get_template(self, template_id: str) -> PostTemplate | None:
        """Get a template by ID."""
        return self.templates.get(template_id)
    
    def create_post_from_template(self, template_id: str, variables: dict[str, str]) -> dict[str, Any]:
        """Create post content from template with variables."""
        template = self.get_template(template_id)
        if not template:
            raise ValueError(f"Template not found: {template_id}")
        
        # Replace variables in caption
        caption = template.caption_template
        for var, value in variables.items():
            caption = caption.replace(f"{{{var}}}", value)
        
        # Add default hashtags
        if template.default_hashtags:
            hashtags = " ".join([f"#{tag}" for tag in template.default_hashtags])
            caption = f"{caption}\n\n{hashtags}"
        
        return {
            "caption": caption,
            "media_type": template.media_type,
            "template_id": template_id,
        }
```

### 5. Scheduler (`posting/scheduler.py`)

**Purpose**: Schedule posts for future publication

```python
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from pathlib import Path
import json
import logging

logger = logging.getLogger(__name__)

@dataclass
class ScheduledPost:
    """Scheduled post configuration."""
    post_id: str
    account_id: str
    media_path: str
    caption: str
    scheduled_time: str
    media_type: str
    status: str  # "pending", "posted", "failed"
    created_at: str
    posted_at: str | None = None
    error_message: str | None = None

class PostScheduler:
    """Manage scheduled posts."""
    
    def __init__(self):
        self.scheduled_posts: dict[str, ScheduledPost] = {}
        self._load_scheduled_posts()
    
    def _load_scheduled_posts(self):
        """Load scheduled posts from storage."""
        schedule_file = Path.home() / '.instagram-mcp' / 'scheduled-posts.json'
        if schedule_file.exists():
            with open(schedule_file) as f:
                data = json.load(f)
                for post_data in data['posts']:
                    post = ScheduledPost(**post_data)
                    self.scheduled_posts[post.post_id] = post
    
    def schedule_post(
        self,
        account_id: str,
        media_path: str,
        caption: str,
        scheduled_time: str,
        media_type: str = "photo"
    ) -> ScheduledPost:
        """Schedule a post for future publication."""
        post_id = f"scheduled_{datetime.now().timestamp()}"
        
        post = ScheduledPost(
            post_id=post_id,
            account_id=account_id,
            media_path=media_path,
            caption=caption,
            scheduled_time=scheduled_time,
            media_type=media_type,
            status="pending",
            created_at=datetime.now().isoformat()
        )
        
        self.scheduled_posts[post_id] = post
        self._save_scheduled_posts()
        return post
    
    def get_due_posts(self) -> list[ScheduledPost]:
        """Get posts that are due for publication."""
        now = datetime.now()
        due_posts = []
        
        for post in self.scheduled_posts.values():
            if post.status == "pending":
                scheduled_time = datetime.fromisoformat(post.scheduled_time)
                if scheduled_time <= now:
                    due_posts.append(post)
        
        return due_posts
    
    def mark_posted(self, post_id: str, error_message: str | None = None):
        """Mark a post as posted or failed."""
        if post_id in self.scheduled_posts:
            post = self.scheduled_posts[post_id]
            post.status = "posted" if not error_message else "failed"
            post.posted_at = datetime.now().isoformat()
            post.error_message = error_message
            self._save_scheduled_posts()
```

### 6. Queue (`posting/queue.py`)

**Purpose**: Manage posting queue with rate limiting and retry logic

```python
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any
import logging

logger = logging.getLogger(__name__)

@dataclass
class QueuedPost:
    """Post in the posting queue."""
    post_id: str
    account_id: str
    media_path: str
    caption: str
    media_type: str
    priority: int  # 1-10, lower is higher priority
    attempts: int = 0
    max_attempts: int = 3
    cooldown_until: str | None = None
    error_message: str | None = None
    created_at: str = datetime.now().isoformat()

class PostingQueue:
    """Manage posting queue with rate limiting."""
    
    def __init__(self):
        self.queue: list[QueuedPost] = []
        self.min_post_interval = timedelta(minutes=30)  # Minimum 30 minutes between posts
        self.last_post_time: dict[str, datetime] = {}  # Account -> last post time
    
    def add_to_queue(
        self,
        account_id: str,
        media_path: str,
        caption: str,
        media_type: str = "photo",
        priority: int = 5
    ) -> QueuedPost:
        """Add a post to the queue."""
        post_id = f"queued_{datetime.now().timestamp()}"
        
        post = QueuedPost(
            post_id=post_id,
            account_id=account_id,
            media_path=media_path,
            caption=caption,
            media_type=media_type,
            priority=priority
        )
        
        # Insert in priority order
        self.queue.append(post)
        self.queue.sort(key=lambda x: x.priority)
        return post
    
    def get_next_post(self) -> QueuedPost | None:
        """Get the next post that can be posted (respecting cooldowns)."""
        now = datetime.now()
        
        for post in self.queue:
            # Check if account is in cooldown
            if post.account_id in self.last_post_time:
                last_post = self.last_post_time[post.account_id]
                if now - last_post < self.min_post_interval:
                    continue
            
            # Check if post is in cooldown
            if post.cooldown_until:
                cooldown_end = datetime.fromisoformat(post.cooldown_until)
                if now < cooldown_end:
                    continue
            
            return post
        
        return None
    
    def mark_posted(self, post_id: str):
        """Mark a post as successfully posted."""
        post = next((p for p in self.queue if p.post_id == post_id), None)
        if post:
            self.queue.remove(post)
            self.last_post_time[post.account_id] = datetime.now()
    
    def mark_failed(self, post_id: str, error_message: str):
        """Mark a post as failed and schedule retry."""
        post = next((p for p in self.queue if p.post_id == post_id), None)
        if post:
            post.attempts += 1
            post.error_message = error_message
            
            if post.attempts >= post.max_attempts:
                # Remove from queue if max attempts reached
                self.queue.remove(post)
            else:
                # Schedule retry with exponential backoff
                backoff_minutes = 2 ** post.attempts * 5
                post.cooldown_until = (datetime.now() + timedelta(minutes=backoff_minutes)).isoformat()
```

## Integration with Existing Architecture

### Dependency Integration

**Update `dependencies.py`**:

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

### Multi-Account Integration

The posting module will use the existing multi-account system:

```python
# Uses existing functions from multi_account.py
from instagram_mcp_server.multi_account import (
    get_account_cookies,
    get_active_account,
    list_accounts,
    update_account_last_used
)

# PostingClient automatically uses account-specific cookies
posting_client = PostingClient(account_id="business_account")
```

### Tool Registration Pattern

Follow the existing pattern from other tool modules:

```python
# instagram_mcp_server/tools/posting_tools.py
from instagram_mcp_server.posting.client import PostingClient
from instagram_mcp_server.dependencies import get_ready_posting_client
from instagram_mcp_server.tools._guard import tool_guard

def register_posting_tools(mcp: FastMCP) -> None:
    """Register all posting-related tools with the MCP server."""
    
    @mcp.tool(
        timeout=TOOL_TIMEOUT_SECONDS,
        title="Upload Photo",
        annotations={"destructiveHint": True, "openWorldHint": True},
        tags={"posting", "media"},
    )
    @tool_guard("upload_photo")
    async def upload_photo(
        image_path: str,
        caption: str,
        account_id: str | None = None,
        ctx: Context = CurrentContext(),
    ) -> dict[str, Any]:
        """Upload a photo to Instagram feed."""
        client = await get_ready_posting_client(ctx, tool_name="upload_photo", account_id=account_id)
        # Implementation here
```

## Error Handling Strategy

### Instagram-Specific Errors

```python
from instagrapi.exceptions import (
    ChallengeRequired,
    LoginRequired,
    FeedbackRequired,
    RelayRequired,
    SentryBlock,
    IPBlock,
)

class PostingErrorHandler:
    """Handle Instagram posting errors."""
    
    @staticmethod
    def handle_instagrapi_error(error: Exception) -> tuple[bool, str]:
        """Handle instagrapi-specific errors."""
        if isinstance(error, ChallengeRequired):
            return False, "Challenge required - manual intervention needed"
        elif isinstance(error, LoginRequired):
            return False, "Login required - session expired"
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

## File Storage Structure

```
~/.instagram-mcp/
├── accounts/
│   ├── [account_id]/
│   │   ├── account-metadata.json
│   │   └── cookies.json
│   └── triggers/
│       ├── triggers-config.json
│       └── executions/
├── templates.json              # NEW: Post templates
├── scheduled-posts.json         # NEW: Scheduled posts
└── posting-queue.json          # NEW: Posting queue state
```

## Performance Considerations

### Resource Management

- **Memory**: Video processing requires 2GB+ RAM
- **CPU**: Video encoding is CPU-intensive
- **Storage**: Temporary files need cleanup
- **Network**: Uploads require bandwidth monitoring

### Rate Limiting

- **Per-Account**: Minimum 30 minutes between posts
- **Per-IP**: Global rate limits across accounts
- **Content Type**: Different limits for photos vs videos
- **Challenge Detection**: Automatic cooldown on errors

## Security Considerations

### Media File Handling

- **Validation**: Validate all media files before processing
- **Sanitization**: Sanitize file paths to prevent directory traversal
- **Size Limits**: Enforce maximum file sizes
- **Type Checking**: Verify MIME types
- **Cleanup**: Remove temporary files after processing

### Account Security

- **Cookie Protection**: Use existing secure cookie storage
- **Session Validation**: Validate sessions before posting
- **Error Handling**: Don't expose sensitive error information
- **Access Control**: Respect account-level permissions

This architecture provides a robust foundation for implementing media posting capabilities while maintaining clean integration with the existing codebase structure.