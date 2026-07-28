# Instagram Specifications Upgrade Plan

## Current Infrastructure Issues

### Outdated Specifications
The current implementation uses outdated Instagram specifications that limit modern content creation:

**Current Limits:**
- **Reels/Feed Videos**: Max 60 seconds (should be 180s+)
- **Stories**: Max 15 seconds (should be 60s)
- **Feed Posts**: Forced 1:1 aspect ratio (should support 4:5 as standard)
- **Aspect Ratios**: Limited to 1:1 and 9:16 (should support 1.91:1 to 4:5 range)

## Research Findings: Instagram 2025 Specifications

### Video Duration Limits
| Format | Current Limit | Actual Limit | Recommended |
|--------|---------------|--------------|-------------|
| Reels | 60s | 3s - 15 min | 3s - 180s (safe) |
| Stories | 15s | 1s - 60s | 1s - 60s |
| Feed Videos | 60s | 3s - 60 min | 3s - 180s (safe) |
| Live | N/A | Up to 4 hours | N/A |

### Aspect Ratio Specifications
| Format | Current | Standard | Instagram Supported |
|--------|---------|----------|-------------------|
| Feed Posts | 1:1 forced | 4:5 portrait | 1.91:1 to 4:5 |
| Reels | 9:16 | 9:16 | 9:16 only |
| Stories | 9:16 | 9:16 | 9:16 + 1.91:1 to 4:5 |
| Carousels | 1:1 forced | 4:5 portrait | 1.91:1 to 4:5 |

### Modern Best Practices
- **4:5 Aspect Ratio**: Industry standard for feed posts (1080x1350)
- **9:16**: Required for Reels and Stories (1080x1920)
- **1.91:1**: Landscape format for feed (1920x1080)
- **Video Duration**: Reels up to 3 minutes commonly used, Stories up to 60s

## Infrastructure Upgrade Plan

### Phase 1: Configuration Updates

#### 1.1 Update Media Processor Constants
**File**: `instagram_mcp_server/posting/media_processor.py`

**Changes Required:**
```python
# OLD (outdated)
MAX_IMAGE_SIZE = 1080  # pixels
MAX_VIDEO_DURATION = 60  # seconds for Reels
MAX_STORY_DURATION = 15  # seconds for Stories
STORY_ASPECT_RATIO = (9, 16)  # 9:16 for stories
FEED_ASPECT_RATIO = (1, 1)  # 1:1 for feed posts

# NEW (current Instagram specs)
MAX_IMAGE_SIZE = 1080  # pixels (unchanged)
MAX_VIDEO_DURATION = 180  # seconds for Reels/Feed (3 minutes)
MAX_STORY_DURATION = 60  # seconds for Stories
STORY_ASPECT_RATIO = (9, 16)  # 9:16 for stories
FEED_ASPECT_RATIO = (4, 5)  # 4:5 for feed posts (industry standard)
LANDSCAPE_ASPECT_RATIO = (16, 9)  # 16:9 for landscape feed posts
```

#### 1.2 Update Validator Constants
**File**: `instagram_mcp_server/posting/validators.py`

**Changes Required:**
```python
# OLD
MAX_VIDEO_DURATION = 60  # seconds for Reels
MAX_STORY_DURATION = 15  # seconds for Stories

# NEW
MAX_VIDEO_DURATION = 180  # seconds for Reels/Feed
MAX_STORY_DURATION = 60  # seconds for Stories
MAX_LIVE_DURATION = 14400  # 4 hours (optional for future)

# Add aspect ratio validation
VALID_ASPECT_RATIOS = {
    'feed': [(4, 5), (1, 1), (16, 9)],  # 4:5, 1:1, 16:9
    'reels': [(9, 16)],  # 9:16 only
    'stories': [(9, 16), (4, 5), (1, 1)],  # 9:16 preferred, others accepted
}
```

### Phase 2: Media Processing Enhancements

#### 2.1 Flexible Aspect Ratio Processing
**File**: `instagram_mcp_server/posting/media_processor.py`

**New Method:**
```python
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
    """
    img = Image.open(image_path)
    
    # Convert to RGB if necessary
    if img.mode in ('RGBA', 'P'):
        img = img.convert('RGB')
    
    # Only force aspect ratio if specified
    if target_aspect and force_aspect:
        img = MediaProcessor._resize_to_aspect(img, target_aspect)
    
    # Compress to max dimensions
    img = MediaProcessor._compress_image(img, max_size)
    
    # Save to temp file
    temp_path = MediaProcessor._save_temp_image(img)
    return temp_path
```

#### 2.2 Smart Video Duration Handling
**File**: `instagram_mcp_server/posting/media_processor.py`

**Enhanced Method:**
```python
@staticmethod
def process_video(
    video_path: str,
    is_story: bool = False,
    max_duration: int | None = None
) -> tuple[str, str]:
    """Process video for Instagram with flexible duration handling.
    
    Args:
        video_path: Path to video file
        is_story: Whether this is for a story (affects duration limits)
        max_duration: Custom max duration (overrides defaults)
        
    Returns:
        Tuple of (processed_video_path, thumbnail_path)
    """
    # Use provided max_duration or defaults
    if max_duration is None:
        max_duration = MediaProcessor.MAX_STORY_DURATION if is_story else MediaProcessor.MAX_VIDEO_DURATION
    
    video = VideoFileClip(video_path)
    
    # Only trim if exceeds limit
    if video.duration > max_duration:
        logger.warning(f"Video duration {video.duration}s exceeds limit {max_duration}s, trimming")
        video = video.subclip(0, max_duration)
    else:
        logger.info(f"Video duration {video.duration}s within limit {max_duration}s")
    
    # Generate thumbnail and compress
    # ... existing code ...
```

### Phase 3: Tool Parameter Updates

#### 3.1 Add Aspect Ratio Options to Upload Tools
**File**: `instagram_mcp_server/tools/posting_tools.py`

**New Parameters:**
```python
async def upload_photo(
    image_path: str,
    caption: str,
    aspect_ratio: str = "4:5",  # NEW: "4:5", "1:1", "16:9", "auto"
    force_aspect: bool = False,  # NEW: force aspect ratio conversion
    # ... existing parameters ...
):
    """Upload photo with flexible aspect ratio options."""
    
    # Convert aspect ratio string to tuple
    aspect_map = {
        "4:5": (4, 5),
        "1:1": (1, 1),
        "16:9": (16, 9),
        "auto": None,
    }
    target_aspect = aspect_map.get(aspect_ratio, (4, 5))
    
    # Process with flexible aspect ratio
    if aspect_ratio == "auto":
        processed_path = MediaProcessor.process_image_flexible(
            image_path, target_aspect=None, force_aspect=False
        )
    else:
        processed_path = MediaProcessor.process_image_flexible(
            image_path, target_aspect=target_aspect, force_aspect=force_aspect
        )
```

#### 3.2 Add Duration Options to Video Tools
**File**: `instagram_mcp_server/tools/posting_tools.py`

**New Parameters:**
```python
async def upload_video(
    video_path: str,
    caption: str,
    max_duration: int | None = None,  # NEW: custom duration limit
    # ... existing parameters ...
):
    """Upload video with flexible duration options."""
    
    # Process video with custom duration
    processed_path, thumbnail_path = MediaProcessor.process_video(
        video_path, 
        is_story=False,
        max_duration=max_duration
    )
```

### Phase 4: Validation Updates

#### 4.1 Enhanced Aspect Ratio Validation
**File**: `instagram_mcp_server/posting/validators.py`

**New Method:**
```python
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
    aspect_ratio = width / height
    
    valid_ratios = {
        'feed': [(4/5, 1.91/1), (1/1, 1/1)],  # 4:5 to 1.91:1
        'reels': [(9/16, 9/16)],  # 9:16 only
        'stories': [(9/16, 9/16), (4/5, 4/5), (1/1, 1/1)],  # Multiple options
    }
    
    min_ratio, max_ratio = valid_ratios.get(media_type, [(0.8, 1.91)])[0]
    
    if not (min_ratio <= aspect_ratio <= max_ratio):
        return False, f"Invalid aspect ratio {width}:{height} for {media_type}"
    
    return True, ""
```

### Phase 5: Testing Updates

#### 5.1 Update Test Constants
**File**: `tests/test_posting_tools.py`

**Changes Required:**
```python
# Update test expectations
MAX_VIDEO_DURATION = 180  # Updated from 60
MAX_STORY_DURATION = 60  # Updated from 15
DEFAULT_ASPECT_RATIO = (4, 5)  # Updated from (1, 1)
```

#### 5.2 Add New Test Cases
- Test 4:5 aspect ratio processing
- Test 16:9 landscape processing
- Test 180-second video processing
- Test 60-second story processing
- Test auto aspect ratio preservation
- Test flexible duration limits

## Implementation Priority

### High Priority (Week 1)
1. ✅ Update constants in media_processor.py
2. ✅ Update constants in validators.py
3. ✅ Add flexible aspect ratio processing
4. ✅ Update video duration handling
5. ✅ Update tool parameters

### Medium Priority (Week 2)
6. ✅ Add aspect ratio validation
7. ✅ Update test suite
8. ✅ Add new test cases
9. ✅ Update documentation

### Low Priority (Week 3)
10. Add advanced video processing options
11. Add batch processing support
12. Add quality presets
13. Performance optimization

## Backward Compatibility

### Breaking Changes
- Default aspect ratio changes from 1:1 to 4:5
- Default video duration increases from 60s to 180s
- Default story duration increases from 15s to 60s

### Migration Strategy
1. Add deprecation warnings for old behavior
2. Provide compatibility mode for legacy code
3. Document migration path
4. Update examples and tutorials

## Success Metrics

### Functional Requirements
- ✅ Support 4:5 aspect ratio for feed posts
- ✅ Support 16:9 landscape for feed posts
- ✅ Support 180-second videos for Reels
- ✅ Support 60-second videos for Stories
- ✅ Preserve original aspect ratio when requested
- ✅ Flexible duration limits

### Performance Requirements
- Processing time within 10% of current implementation
- Memory usage within 20% of current implementation
- No quality degradation

### Quality Requirements
- All existing tests pass
- New tests for updated functionality
- Integration tests pass
- Manual testing with real Instagram uploads

## Risk Assessment

### Technical Risks
- **Medium**: Instagram API changes during implementation
- **Low**: Performance degradation with larger videos
- **Low**: Aspect ratio conversion quality issues

### Mitigation Strategies
- Monitor Instagram API documentation
- Implement performance testing
- Add quality validation
- Gradual rollout with feature flags

## References

### Instagram Official Documentation
- [Instagram Ads API Media Requirements](https://developers.facebook.com/docs/instagram/ads-api/reference/media-requirements/)
- [Instagram Help Center](https://help.instagram.com/)

### Industry Best Practices
- Hootsuite Instagram Video Sizes Guide
- Sprout Social Video Specs Guide
- Growthscribe Instagram Format Guide

### Technical References
- instagrapi Documentation
- Instagram Private API Documentation
- MoviePy Video Processing Library

---

**Document Version**: 1.0  
**Last Updated**: 2026-07-29  
**Status**: Ready for Implementation