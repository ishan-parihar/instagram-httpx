# Dependency Additions Plan for Media Processing

## Required Dependencies

### Core Posting Library

```toml
[project.dependencies]
instagrapi = ">=2.5.0"
```

**Purpose**: Instagram private API client for media posting
**Features**: Photo, video, carousel, story, reel posting
**Maintenance**: Actively maintained (Oct 2025)
**Compatibility**: Python 3.10+

### Image Processing

```toml
[project.dependencies]
Pillow = ">=10.0.0"
```

**Purpose**: Image processing (resize, compress, format conversion)
**Features**: 
- Image resizing and aspect ratio adjustment
- JPEG/PNG compression and optimization
- Thumbnail generation
- Image validation and format checking
**Maintenance**: Well-maintained, industry standard
**Alternative**: ImageMagick (requires system installation)

### Video Processing

```toml
[project.dependencies]
moviepy = ">=1.0.0"
ffmpeg-python = ">=0.2.0"
```

**Purpose**: Video processing for Instagram specifications
**Features**:
- Video compression and optimization
- Duration limiting (60s for Reels, 15s for Stories)
- Aspect ratio adjustment
- Thumbnail generation
- Format conversion to MP4
**Maintenance**: Active development
**System Requirements**: Requires FFmpeg system installation

### Optional Enhanced Dependencies

```toml
[project.optional-dependencies]
media-posting = [
    "instagrapi>=2.5.0",
    "Pillow>=10.0.0",
    "moviepy>=1.0.0",
    "ffmpeg-python>=0.2.0",
]
```

**Purpose**: Optional installation for users who only need posting features
**Usage**: `pip install -e ".[media-posting]"`

## Dependency Analysis

### Instagrapi

**Current Version**: 2.5.17 (Oct 2025)
**Size**: ~5MB
**Transitive Dependencies**: 
- requests (HTTP client)
- pydantic (data validation)
- PyYAML (configuration)
- Other Python packages

**Pros**:
- Battle-tested with extensive real-world usage
- Comprehensive documentation and examples
- Active community support
- Proven track record for media posting

**Cons**:
- Additional dependency overhead
- Requires session management to avoid challenges
- Instagram frequently changes API, requires updates

### Pillow

**Current Version**: 10.0.0+
**Size**: ~3MB
**Transitive Dependencies**: Minimal (few external deps)

**Pros**:
- Industry standard for image processing
- Excellent documentation
- Supports all required image operations
- No system dependencies required

**Cons**:
- Large library for simple operations
- May not need all features

**Alternative**: ImageMagick (requires system installation, more complex)

### MoviePy + FFmpeg

**Current Version**: moviepy 1.0.0+, ffmpeg-python 0.2.0+
**Size**: ~50MB (including FFmpeg)
**System Requirements**: FFmpeg must be installed separately

**Pros**:
- Pythonic interface to FFmpeg
- Comprehensive video processing capabilities
- Well-documented
- Industry standard for video processing

**Cons**:
- Requires FFmpeg system installation
- Large dependency footprint
- Complex installation process

**Alternative**: Use instagrapi's built-in video handling (requires system FFmpeg)

## Installation Strategy

### Standard Installation

**Option 1: Full Installation (Recommended)**
```bash
# Add to pyproject.toml dependencies
pip install instagrapi Pillow moviepy ffmpeg-python

# Install FFmpeg system dependency
# Ubuntu/Debian:
sudo apt-get install ffmpeg

# macOS:
brew install ffmpeg

# Windows:
# Download from https://ffmpeg.org/download.html
```

**Option 2: Minimal Installation**
```bash
# Only essential dependencies
pip install instagrapi Pillow

# Skip video processing initially
# Use instagrapi's built-in video handling (requires FFmpeg)
```

**Option 3: Optional Installation**
```bash
# Install core package first
pip install -e instagram-lyr

# Then add posting capabilities
pip install -e instagram-lyr[media-posting]
```

## FFmpeg Installation Guide

### Linux (Ubuntu/Debian)
```bash
sudo apt-get update
sudo apt-get install ffmpeg

# Verify installation
ffmpeg -version
```

### macOS
```bash
brew install ffmpeg

# Verify installation
ffmpeg -version
```

### Windows
```bash
# Download from https://ffmpeg.org/download.html
# Add to system PATH
# Verify installation
ffmpeg -version
```

### Docker Integration
```dockerfile
# Add to Dockerfile
RUN apt-get update && apt-get install -y ffmpeg

# Or use multi-stage build for smaller final image
```

## Dependency Management

### Version Pinning Strategy

**Pin Major Versions** (recommended for stability):
```toml
[project.dependencies]
instagrapi = ">=2.5.0,<3.0.0"
Pillow = ">=10.0.0,<11.0.0"
moviepy = ">=1.0.0,<2.0.0"
ffmpeg-python = ">=0.2.0,<1.0.0"
```

**Exact Version Pinning** (for maximum stability):
```toml
[project.dependencies]
instagrapi = "==2.5.17"
Pillow = "==10.0.0"
moviepy = "==1.0.3"
ffmpeg-python = "==0.2.0"
```

### Compatibility Checks

**Python Version**: Ensure Python 3.10+ (instagrapi requirement)
```bash
python --version  # Should be 3.10+
```

**System FFmpeg**: Verify FFmpeg installation
```bash
ffmpeg -version  # Should show version info
```

**Image Libraries**: Test Pillow installation
```python
from PIL import Image
print(Image.__version__)  # Should work without errors
```

## Performance Impact Analysis

### Memory Impact

**Current Memory Usage**: ~100-200MB (httpx + scraping)
**With Media Processing**: ~300-500MB (adding Pillow + moviepy)
**Peak During Video Processing**: ~1-2GB (video encoding)

**Recommendation**: Increase systemd MemoryMax to 2GB for media posting

### Disk Space Impact

**Installation Size**: ~60MB additional
**Temporary Files**: 100-500MB during processing
**Storage Requirements**: Need ReadWritePaths for `/tmp/instagram-media`

**Recommendation**: Add temp directory cleanup and monitoring

### CPU Impact

**Current CPU Usage**: Low (mostly network I/O)
**With Media Processing**: High during video encoding
**Peak During Upload**: Medium (network I/O + encoding)

**Recommendation**: Increase CPUQuota to 100% for media posting

## Error Handling for Dependencies

### Missing FFmpeg

```python
def check_ffmpeg_available() -> bool:
    """Check if FFmpeg is available."""
    try:
        import subprocess
        result = subprocess.run(['ffmpeg', '-version'], 
                              capture_output=True, text=True)
        return result.returncode == 0
    except FileNotFoundError:
        return False

if not check_ffmpeg_available():
    raise RuntimeError(
        "FFmpeg is required for video processing. "
        "Install with: sudo apt-get install ffmpeg (Linux) or brew install ffmpeg (macOS)"
    )
```

### Missing Dependencies

```python
def check_dependencies() -> dict[str, bool]:
    """Check if all required dependencies are available."""
    dependencies = {
        'instagrapi': False,
        'Pillow': False,
        'moviepy': False,
        'ffmpeg': False,
    }
    
    try:
        import instagrapi
        dependencies['instagrapi'] = True
    except ImportError:
        pass
    
    try:
        from PIL import Image
        dependencies['Pillow'] = True
    except ImportError:
        pass
    
    try:
        import moviepy
        dependencies['moviepy'] = True
    except ImportError:
        pass
    
    dependencies['ffmpeg'] = check_ffmpeg_available()
    
    return dependencies
```

## Gradual Rollout Strategy

### Phase 1: Photo Posting Only (Week 1)
```toml
[project.dependencies]
instagrapi = ">=2.5.0"
Pillow = ">=10.0.0"
```

**Benefits**: 
- Minimal dependencies
- Lower resource requirements
- Faster implementation
- Prove concept before full investment

### Phase 2: Add Video Support (Week 2)
```toml
[project.dependencies]
instagrapi = ">=2.5.0"
Pillow = ">=10.0.0"
moviepy = ">=1.0.0"
ffmpeg-python = ">=0.2.0"
```

**Benefits**:
- Complete posting capabilities
- Full feature set
- Comprehensive testing

### Phase 3: Advanced Features (Week 3-4)
```toml
[project.optional-dependencies]
advanced-posting = [
    "opencv-python>=4.0.0",  # Advanced image processing
    "scikit-image>=0.19.0",  # Image analysis
    "google-cloud-storage",  # Cloud storage integration
]
```

## Testing Strategy

### Dependency Testing

```python
# tests/test_dependencies.py
def test_instagrapi_available():
    """Test instagrapi installation."""
    try:
        import instagrapi
        assert instagrapi.__version__ >= "2.5.0"
    except ImportError:
        pytest.fail("instagrapi not installed")

def test_pillow_available():
    """Test Pillow installation."""
    try:
        from PIL import Image
        assert Image.__version__ >= "10.0.0"
    except ImportError:
        pytest.fail("Pillow not installed")

def test_ffmpeg_available():
    """Test FFmpeg installation."""
    import subprocess
    result = subprocess.run(['ffmpeg', '-version'], 
                          capture_output=True, text=True)
    assert result.returncode == 0, "FFmpeg not installed"
```

### Integration Testing

```python
# tests/test_posting_integration.py
def test_photo_upload_with_dependencies():
    """Test photo upload with all dependencies."""
    from instagram_mcp_server.posting.client import PostingClient
    from instagram_mcp_server.posting.media_processor import MediaProcessor
    
    # Test with actual dependencies
    client = PostingClient(account_id="test_account")
    processor = MediaProcessor()
    
    # Test image processing
    processed_image = processor.process_image("test.jpg")
    assert Path(processed_image).exists()
    
    # Test upload (with mock instagrapi)
    # Would need to mock instagrapi for CI/CD
```

## Backward Compatibility

### Current Users

**Impact**: Minimal - no changes to existing functionality
**Risk**: None - new dependencies are optional for posting features only
**Migration**: No migration needed - existing features unchanged

### New Users

**Experience**: Full feature set available immediately
**Installation**: Standard pip install includes all dependencies
**Configuration**: FFmpeg may need separate installation

## Rollback Plan

If issues arise with new dependencies:

1. **Feature Flags**: Add feature flags to disable posting features
2. **Graceful Degradation**: Existing scraping features continue to work
3. **Error Messages**: Clear error messages when dependencies missing
4. **Fallback**: Fallback to basic operations if video processing fails

## Monitoring and Maintenance

### Dependency Updates

**Strategy**: Regular dependency updates for security patches
**Frequency**: Monthly security updates
**Testing**: Test each update in staging environment

### Known Issues

**Instagrapi Login Issues**: Instagram frequently changes login flow
**Mitigation**: Use sessionid-based login, avoid password-based login
**FFmpeg Compatibility**: Different FFmpeg versions may have issues
**Mitigation**: Pin to specific FFmpeg version in documentation

## Conclusion

**Recommended Approach**: Implement phased dependency addition starting with photo posting only, then add video processing capabilities. This reduces risk and allows for incremental testing and validation.

**Timeline**:
- Week 1: Add instagrapi + Pillow (photo posting)
- Week 2: Add moviepy + ffmpeg-python (video posting)
- Week 3-4: Advanced features and optimization

**Resource Planning**: Increase system resources for media processing (2GB RAM, 100% CPU, additional storage).

**Backup Plan**: Maintain current scraping functionality independently of posting features to ensure system stability.