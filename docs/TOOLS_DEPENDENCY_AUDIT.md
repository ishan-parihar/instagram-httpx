# Tools Dependency Audit

## Overview
Audit of non-essential tools with external dependencies that can be purged or marked as optional.

## Tool Categories

### 🔴 RED - Recommended for Removal

#### insights.py
- **Status**: Already deprecated
- **Dependencies**: None (tools don't work)
- **Reason**: Professional Dashboard not accessible via Instagram's private-web API
- **Action**: **REMOVE ENTIRELY**
- **Tools Affected**:
  - `get_business_insights` (deprecated)
  - `get_content_insights` (deprecated)  
  - `get_stories_insights` (deprecated)
  - `get_audience_insights` (deprecated)

### 🟡 YELLOW - Optional - External API Required

#### gemini_analysis.py
- **Status**: Functional but optional
- **Dependencies**: 
  - `google-genai>=1.0.0` (package)
  - `GEMINI_API_KEY` environment variable
  - Google Gemini 2.0 Flash API (paid service)
- **Reason**: Requires paid API key and external service
- **Cost**: ~$0.00017 per reel
- **Action**: **MARK AS OPTIONAL** (install via extra dependency)
- **Tools Affected**:
  - `analyze_reel_with_gemini`
  - `bulk_analyze_reels_with_gemini`

### 🟠 ORANGE - Optional - Heavy Local Dependencies

#### transcription.py
- **Status**: Functional but heavy dependencies
- **Dependencies**:
  - Conda environment `whisper-hindi`
  - `whisper_timestamped` package
  - `ffmpeg` for audio extraction
  - Apex Whisper model
- **Reason**: Requires full conda environment setup
- **Action**: **MARK AS OPTIONAL** (requires manual setup)
- **Tools Affected**:
  - `transcribe_user_reels`
  - `transcribe_reel`

#### apex_transcriber.py
- **Status**: Support module for transcription
- **Dependencies**:
  - Conda environment `whisper-hindi`
  - Whisper-Hindi2Hinglish-Apex model
  - `ffmpeg` for audio extraction
- **Reason**: Support module for heavy transcription
- **Action**: **REMOVE WITH transcription.py**

### 🟢 GREEN - Essential - Keep

#### All other tools
- **Dependencies**: Core package dependencies only
- **Status**: Essential for core functionality
- **Action**: **KEEP**

## Recommended Actions

### 1. Remove Deprecated Tools
```bash
# Remove insights.py entirely
rm instagram_mcp_server/tools/insights.py
# Remove registration from server.py
```

### 2. Make Transcription Optional
```bash
# Remove from core dependencies
# Add to optional dependencies in pyproject.toml
# Add environment variable checks to disable if not configured
```

### 3. Make Gemini Analysis Optional  
```bash
# Move google-genai to optional dependencies
# Add GEMINI_API_KEY checks to disable if not configured
```

## Updated Dependency Structure

### Core Dependencies (Keep)
- `fastmcp>=3.0.0`
- `httpx>=0.28.1`
- `inquirer>=3.4.0`
- `python-dotenv>=1.1.1`
- `instagrapi>=2.5.0`
- `Pillow>=10.0.0`
- `moviepy>=1.0.0`

### Optional Dependencies (Move to extras)
- `google-genai>=1.0.0` (for gemini analysis)
- `ffmpeg-python>=0.2.0` (can be moved to optional)

### Manual Dependencies (Documentation only)
- Conda environment `whisper-hindi` (for transcription)
- `ffmpeg` system binary (for audio extraction)

## Implementation Priority

1. **HIGH**: Remove deprecated insights.py
2. **MEDIUM**: Make transcription tools optional with environment checks
3. **MEDIUM**: Make gemini analysis optional with API key checks
4. **LOW**: Clean up apex_transcriber.py support module

## Environmental Checks

Add these environment variable checks to disable optional tools:

```python
# Transcription tools
if not os.environ.get("INSTAGRAM_MCP_ENABLE_TRANSCRIPTION"):
    # Skip registration of transcription tools
    
# Gemini tools  
if not os.environ.get("GEMINI_API_KEY"):
    # Skip registration of gemini tools
```

## Testing Plan

1. Test core functionality without optional dependencies
2. Test optional tools when dependencies are present
3. Verify graceful degradation when optional tools are disabled
4. Update installation documentation for optional features