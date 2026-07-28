# Content Creation System Comprehensive Testing Plan

## Test Scope
This plan covers full-scope testing of Instagram content creation features including photo, video, carousel, story, and reel posting with advanced features.

## Test Environment Setup
- **Required**: Valid Instagram account with session cookies
- **Test Account**: Dedicated test account (to avoid affecting production)
- **Test Media**: Sample images and videos for testing
- **Test Locations**: Valid Instagram location IDs
- **Test Users**: Coordinated users for tagging tests

## Test Categories

### 1. Photo Posting Tests

#### 1.1 Basic Photo Upload
**Test Cases:**
- **TC-PH-001**: Upload JPG photo with caption
  - Input: Valid JPG image, caption < 2200 chars
  - Expected: Photo uploaded successfully, post URL returned
  - Validation: Post appears on Instagram feed

- **TC-PH-002**: Upload PNG photo with caption
  - Input: Valid PNG image, caption < 2200 chars
  - Expected: Photo uploaded successfully
  - Validation: PNG format accepted

- **TC-PH-003**: Upload photo without caption
  - Input: Valid image, caption=""
  - Expected: Photo uploaded successfully
  - Validation: Empty caption accepted

- **TC-PH-004**: Upload photo with maximum caption length
  - Input: Valid image, caption = 2200 characters
  - Expected: Photo uploaded successfully
  - Validation: Maximum caption length accepted

- **TC-PH-005**: Upload photo with caption exceeding limit
  - Input: Valid image, caption > 2200 characters
  - Expected: Error returned
  - Validation: Caption length validation works

- **TC-PH-006**: Upload invalid image format
  - Input: Invalid file format (e.g., .gif, .bmp)
  - Expected: Error returned
  - Validation: Format validation works

- **TC-PH-007**: Upload non-existent file
  - Input: Invalid file path
  - Expected: Error returned
  - Validation: File existence validation works

- **TC-PH-008**: Upload oversized image
  - Input: Image > 1080px width/height
  - Expected: Image processed and resized automatically
  - Validation: Automatic resizing works

#### 1.2 Photo Advanced Features
**Test Cases:**
- **TC-PH-009**: Upload photo with location tag
  - Input: Valid location_id
  - Expected: Photo uploaded with location
  - Validation: Location appears on post

- **TC-PH-010**: Upload photo with user tags
  - Input: user_tags=["username1", "username2"]
  - Expected: Photo uploaded with user tags
  - Validation: Users tagged in post

- **TC-PH-011**: Upload photo with extra data
  - Input: extra_data={"custom_field": "value"}
  - Expected: Photo uploaded with metadata
  - Validation: Extra data preserved

- **TC-PH-012**: Upload photo with Facebook cross-post
  - Input: share_to_facebook=True
  - Expected: Photo uploaded and cross-posted
  - Validation: Post appears on Facebook

- **TC-PH-013**: Upload photo with Threads cross-post
  - Input: share_to_threads=True
  - Expected: Photo uploaded and cross-posted
  - Validation: Post appears on Threads

- **TC-PH-014**: Upload photo with both cross-posts
  - Input: share_to_facebook=True, share_to_threads=True
  - Expected: Photo uploaded and cross-posted to both
  - Validation: Cross-posting to multiple platforms

- **TC-PH-015**: Upload photo with scheduled time
  - Input: schedule_at="2025-12-31T23:59:59Z"
  - Expected: Photo scheduled for future time
  - Validation: Scheduling configuration accepted

- **TC-PH-016**: Upload photo with invalid schedule time
  - Input: schedule_at="invalid_timestamp"
  - Expected: Error returned
  - Validation: Timestamp validation works

#### 1.3 Photo Multi-Account Support
**Test Cases:**
- **TC-PH-017**: Upload photo from specific account
  - Input: account_id="test_account"
  - Expected: Photo uploaded from specified account
  - Validation: Post appears on correct account

- **TC-PH-018**: Upload photo from active account (no account_id)
  - Input: No account_id specified
  - Expected: Photo uploaded from active account
  - Validation: Default account selection works

- **TC-PH-019**: Upload photo with invalid account_id
  - Input: account_id="nonexistent_account"
  - Expected: Error returned
  - Validation: Account validation works

#### 1.4 Photo Posting Limits
**Test Cases:**
- **TC-PH-020**: Respect daily posting limit
  - Setup: Account at daily limit (10 posts)
  - Expected: Upload blocked with limit error
  - Validation: Daily limit enforced

- **TC-PH-021**: Respect cooldown period
  - Setup: Recent post within 30-minute cooldown
  - Expected: Upload blocked with cooldown error
  - Validation: Cooldown enforced

- **TC-PH-022**: Post limit reset after 24 hours
  - Setup: Account at limit, wait 24 hours
  - Expected: Upload allowed after reset
  - Validation: Daily reset works correctly

- **TC-PH-023**: Cooldown expiration
  - Setup: Post at start of cooldown, wait 30 minutes
  - Expected: Upload allowed after cooldown
  - Validation: Cooldown expiration works

#### 1.5 Photo Error Handling
**Test Cases:**
- **TC-PH-024**: Handle authentication failure
  - Setup: Invalid session cookies
  - Expected: Authentication error returned
  - Validation: Error handling works

- **TC-PH-025**: Handle network failure
  - Setup: Simulate network error
  - Expected: Network error returned
  - Validation: Network error handling works

- **TC-PH-026**: Handle Instagram API error
  - Setup: Simulate Instagram API failure
  - Expected: API error returned
  - Validation: API error handling works

- **TC-PH-027**: Record failed post attempt
  - Setup: Intentionally fail upload
  - Expected: Failure recorded in post history
  - Validation: Error logging works

### 2. Video Posting Tests

#### 2.1 Basic Video Upload
**Test Cases:**
- **TC-VD-001**: Upload MP4 video with caption
  - Input: Valid MP4 video (< 60 seconds), caption < 2200 chars
  - Expected: Video uploaded successfully
  - Validation: Video appears on Instagram feed

- **TC-VD-002**: Upload MOV video with caption
  - Input: Valid MOV video (< 60 seconds), caption < 2200 chars
  - Expected: Video uploaded successfully
  - Validation: MOV format accepted

- **TC-VD-003**: Upload video without caption
  - Input: Valid video, caption=""
  - Expected: Video uploaded successfully
  - Validation: Empty caption accepted

- **TC-VD-004**: Upload video with maximum duration
  - Input: Video = 60 seconds
  - Expected: Video uploaded successfully
  - Validation: Maximum duration accepted

- **TC-VD-005**: Upload video exceeding duration limit
  - Input: Video > 60 seconds
  - Expected: Error returned or video processed
  - Validation: Duration validation/processing works

- **TC-VD-006**: Upload invalid video format
  - Input: Invalid file format (e.g., .avi, .wmv)
  - Expected: Error returned
  - Validation: Format validation works

- **TC-VD-007**: Upload non-existent video file
  - Input: Invalid file path
  - Expected: Error returned
  - Validation: File existence validation works

- **TC-VD-008**: Upload corrupted video file
  - Input: Corrupted video file
  - Expected: Error returned
  - Validation: File integrity validation works

#### 2.2 Video Processing
**Test Cases:**
- **TC-VD-009**: Automatic video compression
  - Input: Large video file
  - Expected: Video compressed automatically
  - Validation: Compression works

- **TC-VD-010**: Thumbnail generation
  - Input: Valid video
  - Expected: Thumbnail generated automatically
  - Validation: Thumbnail appears on post

- **TC-VD-011**: Video resolution adjustment
  - Input: High-resolution video
  - Expected: Resolution adjusted to Instagram specs
  - Validation: Automatic processing works

- **TC-VD-012**: Video codec conversion
  - Input: Video with non-standard codec
  - Expected: Codec converted automatically
  - Validation: Codec conversion works

#### 2.3 Video Advanced Features
**Test Cases:**
- **TC-VD-013**: Upload video with location tag
  - Input: Valid location_id
  - Expected: Video uploaded with location
  - Validation: Location appears on post

- **TC-VD-014**: Upload video with user tags
  - Input: user_tags=["username1", "username2"]
  - Expected: Video uploaded with user tags
  - Validation: Users tagged in post

- **TC-VD-015**: Upload video with extra data
  - Input: extra_data={"custom_field": "value"}
  - Expected: Video uploaded with metadata
  - Validation: Extra data preserved

- **TC-VD-016**: Upload video with Facebook cross-post
  - Input: share_to_facebook=True
  - Expected: Video uploaded and cross-posted
  - Validation: Post appears on Facebook

- **TC-VD-017**: Upload video with Threads cross-post
  - Input: share_to_threads=True
  - Expected: Video uploaded and cross-posted
  - Validation: Post appears on Threads

- **TC-VD-018**: Upload video with scheduled time
  - Input: schedule_at="2025-12-31T23:59:59Z"
  - Expected: Video scheduled for future time
  - Validation: Scheduling configuration accepted

#### 2.4 Video Multi-Account & Limits
**Test Cases:**
- **TC-VD-019**: Upload video from specific account
  - Input: account_id="test_account"
  - Expected: Video uploaded from specified account
  - Validation: Post appears on correct account

- **TC-VD-020**: Respect daily posting limit for videos
  - Setup: Account at daily limit
  - Expected: Upload blocked with limit error
  - Validation: Daily limit enforced for videos

- **TC-VD-021**: Respect cooldown period for videos
  - Setup: Recent video post within cooldown
  - Expected: Upload blocked with cooldown error
  - Validation: Cooldown enforced for videos

#### 2.5 Video Error Handling
**Test Cases:**
- **TC-VD-022**: Handle video processing failure
  - Setup: Video that fails processing
  - Expected: Processing error returned
  - Validation: Processing error handling works

- **TC-VD-023**: Handle upload failure
  - Setup: Simulate upload failure
  - Expected: Upload error returned
  - Validation: Upload error handling works

- **TC-VD-024**: Record failed video upload
  - Setup: Intentionally fail video upload
  - Expected: Failure recorded in post history
  - Validation: Error logging works for videos

### 3. Carousel Posting Tests

#### 3.1 Basic Carousel Upload
**Test Cases:**
- **TC-CR-001**: Upload carousel with minimum items (2)
  - Input: 2 valid images, caption < 2200 chars
  - Expected: Carousel uploaded successfully
  - Validation: Carousel appears with 2 items

- **TC-CR-002**: Upload carousel with maximum items (10)
  - Input: 10 valid images, caption < 2200 chars
  - Expected: Carousel uploaded successfully
  - Validation: Carousel appears with 10 items

- **TC-CR-003**: Upload carousel with 5 items
  - Input: 5 valid images, caption < 2200 chars
  - Expected: Carousel uploaded successfully
  - Validation: Carousel appears with 5 items

- **TC-CR-004**: Upload carousel with single item
  - Input: 1 valid image
  - Expected: Error returned
  - Validation: Minimum item validation works

- **TC-CR-005**: Upload carousel with 11 items
  - Input: 11 valid images
  - Expected: Error returned
  - Validation: Maximum item validation works

- **TC-CR-006**: Upload carousel without caption
  - Input: Valid images, caption=""
  - Expected: Carousel uploaded successfully
  - Validation: Empty caption accepted

- **TC-CR-007**: Upload carousel with mixed formats
  - Input: Mix of JPG and PNG images
  - Expected: Carousel uploaded successfully
  - Validation: Mixed format handling works

#### 3.2 Carousel Processing
**Test Cases:**
- **TC-CR-008**: Process all carousel images
  - Input: Multiple images needing processing
  - Expected: All images processed successfully
  - Validation: Complete processing works

- **TC-CR-009**: Handle single image processing failure
  - Input: One invalid image in carousel
  - Expected: Error returned, no carousel uploaded
  - Validation: Partial failure handling works

- **TC-CR-010**: Maintain image order in carousel
  - Input: Ordered list of images
  - Expected: Carousel maintains original order
  - Validation: Image order preserved

#### 3.3 Carousel Advanced Features
**Test Cases:**
- **TC-CR-011**: Upload carousel with location tag
  - Input: Valid location_id
  - Expected: Carousel uploaded with location
  - Validation: Location appears on carousel

- **TC-CR-012**: Upload carousel with user tags
  - Input: user_tags=["username1", "username2"]
  - Expected: Carousel uploaded with user tags
  - Validation: Users tagged in carousel

- **TC-CR-013**: Upload carousel with extra data
  - Input: extra_data={"custom_field": "value"}
  - Expected: Carousel uploaded with metadata
  - Validation: Extra data preserved

- **TC-CR-014**: Upload carousel with Facebook cross-post
  - Input: share_to_facebook=True
  - Expected: Carousel uploaded and cross-posted
  - Validation: Carousel appears on Facebook

- **TC-CR-015**: Upload carousel with Threads cross-post
  - Input: share_to_threads=True
  - Expected: Carousel uploaded and cross-posted
  - Validation: Carousel appears on Threads

- **TC-CR-016**: Upload carousel with scheduled time
  - Input: schedule_at="2025-12-31T23:59:59Z"
  - Expected: Carousel scheduled for future time
  - Validation: Scheduling configuration accepted

#### 3.4 Carousel Multi-Account & Limits
**Test Cases:**
- **TC-CR-017**: Upload carousel from specific account
  - Input: account_id="test_account"
  - Expected: Carousel uploaded from specified account
  - Validation: Carousel appears on correct account

- **TC-CR-018**: Respect daily posting limit for carousels
  - Setup: Account at daily limit
  - Expected: Upload blocked with limit error
  - Validation: Daily limit enforced for carousels

- **TC-CR-019**: Respect cooldown period for carousels
  - Setup: Recent carousel post within cooldown
  - Expected: Upload blocked with cooldown error
  - Validation: Cooldown enforced for carousels

#### 3.5 Carousel Error Handling
**Test Cases:**
- **TC-CR-020**: Handle missing image file
  - Input: One image path doesn't exist
  - Expected: Error returned
  - Validation: File validation works for all items

- **TC-CR-021**: Handle invalid image in carousel
  - Input: One invalid image format
  - Expected: Error returned
  - Validation: Format validation for all items

- **TC-CR-022**: Record failed carousel upload
  - Setup: Intentionally fail carousel upload
  - Expected: Failure recorded in post history
  - Validation: Error logging works for carousels

### 4. Story Posting Tests

#### 4.1 Photo Story Upload
**Test Cases:**
- **TC-ST-001**: Upload photo story with caption
  - Input: Valid image, media_type="photo", caption
  - Expected: Photo story uploaded successfully
  - Validation: Story appears in stories

- **TC-ST-002**: Upload photo story without caption
  - Input: Valid image, media_type="photo", no caption
  - Expected: Photo story uploaded successfully
  - Validation: Story without caption works

- **TC-ST-003**: Upload photo story with 9:16 aspect ratio
  - Input: Image with 9:16 aspect ratio
  - Expected: Photo story uploaded successfully
  - Validation: Correct aspect ratio preserved

- **TC-ST-004**: Upload photo story with wrong aspect ratio
  - Input: Image with 1:1 aspect ratio
  - Expected: Image processed to 9:16 automatically
  - Validation: Automatic aspect ratio conversion

- **TC-ST-005**: Upload photo story with mentions
  - Input: mentions=["username1", "username2"]
  - Expected: Story uploaded with mentions
  - Validation: Mentions appear in story

- **TC-ST-006**: Upload photo story with hashtags
  - Input: hashtags=["hashtag1", "hashtag2"]
  - Expected: Story uploaded with hashtags
  - Validation: Hashtags appear in story

- **TC-ST-007**: Upload photo story with links
  - Input: links=["https://example.com"]
  - Expected: Story uploaded with link stickers
  - Validation: Links appear as stickers

- **TC-ST-008**: Upload photo story with all features
  - Input: mentions, hashtags, links, caption
  - Expected: Story uploaded with all features
  - Validation: All features work together

#### 4.2 Video Story Upload
**Test Cases:**
- **TC-ST-009**: Upload video story with caption
  - Input: Valid video, media_type="video", caption
  - Expected: Video story uploaded successfully
  - Validation: Video story appears in stories

- **TC-ST-010**: Upload video story without caption
  - Input: Valid video, media_type="video", no caption
  - Expected: Video story uploaded successfully
  - Validation: Video story without caption works

- **TC-ST-011**: Upload video story with 15-second duration
  - Input: Video = 15 seconds
  - Expected: Video story uploaded successfully
  - Validation: Maximum story duration accepted

- **TC-ST-012**: Upload video story exceeding duration
  - Input: Video > 15 seconds
  - Expected: Error returned or video processed
  - Validation: Duration validation/processing works

- **TC-ST-013**: Upload video story with mentions
  - Input: mentions=["username1", "username2"]
  - Expected: Video story uploaded with mentions
  - Validation: Mentions appear in video story

- **TC-ST-014**: Upload video story with hashtags
  - Input: hashtags=["hashtag1", "hashtag2"]
  - Expected: Video story uploaded with hashtags
  - Validation: Hashtags appear in video story

- **TC-ST-015**: Upload video story with links
  - Input: links=["https://example.com"]
  - Expected: Video story uploaded with link stickers
  - Validation: Links appear as stickers in video

#### 4.3 Story Media Type Validation
**Test Cases:**
- **TC-ST-016**: Invalid media type
  - Input: media_type="invalid"
  - Expected: Error returned
  - Validation: Media type validation works

- **TC-ST-017**: Missing media type
  - Input: No media_type specified
  - Expected: Error or default to photo
  - Validation: Default behavior handling

#### 4.4 Story Multi-Account & Limits
**Test Cases:**
- **TC-ST-018**: Upload story from specific account
  - Input: account_id="test_account"
  - Expected: Story uploaded from specified account
  - Validation: Story appears on correct account

- **TC-ST-019**: Respect daily posting limit for stories
  - Setup: Account at daily limit
  - Expected: Upload blocked with limit error
  - Validation: Daily limit enforced for stories

- **TC-ST-020**: Respect cooldown period for stories
  - Setup: Recent story post within cooldown
  - Expected: Upload blocked with cooldown error
  - Validation: Cooldown enforced for stories

#### 4.5 Story Error Handling
**Test Cases:**
- **TC-ST-021**: Handle photo story processing failure
  - Setup: Image that fails processing
  - Expected: Processing error returned
  - Validation: Processing error handling works

- **TC-ST-022**: Handle video story processing failure
  - Setup: Video that fails processing
  - Expected: Processing error returned
  - Validation: Video processing error handling works

- **TC-ST-023**: Record failed story upload
  - Setup: Intentionally fail story upload
  - Expected: Failure recorded in post history
  - Validation: Error logging works for stories

### 5. Reel Posting Tests

#### 5.1 Basic Reel Upload
**Test Cases:**
- **TC-RL-001**: Upload reel with caption
  - Input: Valid video (< 60 seconds), caption < 2200 chars
  - Expected: Reel uploaded successfully
  - Validation: Reel appears in reels section

- **TC-RL-002**: Upload reel without caption
  - Input: Valid video, caption=""
  - Expected: Reel uploaded successfully
  - Validation: Empty caption accepted

- **TC-RL-003**: Upload reel with maximum duration
  - Input: Video = 60 seconds
  - Expected: Reel uploaded successfully
  - Validation: Maximum duration accepted

- **TC-RL-004**: Upload reel exceeding duration limit
  - Input: Video > 60 seconds
  - Expected: Error returned or video processed
  - Validation: Duration validation/processing works

- **TC-RL-005**: Upload vertical video (9:16 aspect ratio)
  - Input: Video with 9:16 aspect ratio
  - Expected: Reel uploaded successfully
  - Validation: Vertical format optimized

- **TC-RL-006**: Upload horizontal video (16:9 aspect ratio)
  - Input: Video with 16:9 aspect ratio
  - Expected: Video processed to vertical format
  - Validation: Automatic aspect ratio conversion

- **TC-RL-007**: Upload square video (1:1 aspect ratio)
  - Input: Video with 1:1 aspect ratio
  - Expected: Video processed to vertical format
  - Validation: Aspect ratio conversion works

#### 5.2 Reel Processing
**Test Cases:**
- **TC-RL-008**: Automatic video compression for reels
  - Input: Large video file
  - Expected: Video compressed for reel optimization
  - Validation: Compression works for reels

- **TC-RL-009**: Thumbnail generation for reels
  - Input: Valid video
  - Expected: Thumbnail generated automatically
  - Validation: Thumbnail appears on reel

- **TC-RL-010**: Reel-specific video optimization
  - Input: Standard video
  - Expected: Video optimized for reel format
  - Validation: Reel optimization applied

#### 5.3 Reel Advanced Features
**Test Cases:**
- **TC-RL-011**: Upload reel with location tag
  - Input: Valid location_id
  - Expected: Reel uploaded with location
  - Validation: Location appears on reel

- **TC-RL-012**: Upload reel with user tags
  - Input: user_tags=["username1", "username2"]
  - Expected: Reel uploaded with user tags
  - Validation: Users tagged in reel

- **TC-RL-013**: Upload reel with extra data
  - Input: extra_data={"custom_field": "value"}
  - Expected: Reel uploaded with metadata
  - Validation: Extra data preserved

- **TC-RL-014**: Upload reel with Facebook cross-post
  - Input: share_to_facebook=True
  - Expected: Reel uploaded and cross-posted
  - Validation: Reel appears on Facebook

- **TC-RL-015**: Upload reel with Threads cross-post
  - Input: share_to_threads=True
  - Expected: Reel uploaded and cross-posted
  - Validation: Reel appears on Threads

#### 5.4 Reel Multi-Account & Limits
**Test Cases:**
- **TC-RL-016**: Upload reel from specific account
  - Input: account_id="test_account"
  - Expected: Reel uploaded from specified account
  - Validation: Reel appears on correct account

- **TC-RL-017**: Respect daily posting limit for reels
  - Setup: Account at daily limit
  - Expected: Upload blocked with limit error
  - Validation: Daily limit enforced for reels

- **TC-RL-018**: Respect cooldown period for reels
  - Setup: Recent reel post within cooldown
  - Expected: Upload blocked with cooldown error
  - Validation: Cooldown enforced for reels

#### 5.5 Reel Error Handling
**Test Cases:**
- **TC-RL-019**: Handle reel processing failure
  - Setup: Video that fails processing
  - Expected: Processing error returned
  - Validation: Processing error handling works

- **TC-RL-020**: Handle reel upload failure
  - Setup: Simulate upload failure
  - Expected: Upload error returned
  - Validation: Upload error handling works

- **TC-RL-021**: Record failed reel upload
  - Setup: Intentionally fail reel upload
  - Expected: Failure recorded in post history
  - Validation: Error logging works for reels

### 6. Media Processing Tests

#### 6.1 Image Processing
**Test Cases:**
- **TC-MP-001**: Resize oversized image to 1080px
  - Input: Image > 1080px
  - Expected: Image resized to 1080px
  - Validation: Resizing works correctly

- **TC-MP-002**: Maintain aspect ratio during resize
  - Input: Image with specific aspect ratio
  - Expected: Aspect ratio preserved
  - Validation: Aspect ratio maintenance works

- **TC-MP-003**: Convert PNG to JPG for Instagram
  - Input: PNG image
  - Expected: Converted to JPG format
  - Validation: Format conversion works

- **TC-MP-004**: Optimize image file size
  - Input: Large image file
  - Expected: File size optimized
  - Validation: File size reduction works

- **TC-MP-005**: Process image to 9:16 for stories
  - Input: Image with any aspect ratio
  - Expected: Converted to 9:16 aspect ratio
  - Validation: Story aspect ratio conversion works

#### 6.2 Video Processing
**Test Cases:**
- **TC-MP-006**: Compress video for Instagram
  - Input: Large video file
  - Expected: Video compressed
  - Validation: Compression works

- **TC-MP-007**: Generate thumbnail from video
  - Input: Valid video
  - Expected: Thumbnail generated
  - Validation: Thumbnail generation works

- **TC-MP-008**: Trim video to 60 seconds for feed
  - Input: Video > 60 seconds
  - Expected: Video trimmed to 60 seconds
  - Validation: Video trimming works

- **TC-MP-009**: Trim video to 15 seconds for stories
  - Input: Video > 15 seconds
  - Expected: Video trimmed to 15 seconds
  - Validation: Story video trimming works

- **TC-MP-010**: Convert video codec for Instagram
  - Input: Video with non-standard codec
  - Expected: Codec converted
  - Validation: Codec conversion works

- **TC-MP-011**: Process video to vertical for reels
  - Input: Video with any aspect ratio
  - Expected: Converted to vertical format
  - Validation: Reel aspect ratio conversion works

#### 6.3 Media Validation
**Test Cases:**
- **TC-MP-012**: Validate image file format
  - Input: Various file formats
  - Expected: Only valid formats accepted
  - Validation: Format validation works

- **TC-MP-013**: Validate video file format
  - Input: Various file formats
  - Expected: Only valid formats accepted
  - Validation: Video format validation works

- **TC-MP-014**: Validate image file integrity
  - Input: Corrupted image file
  - Expected: Error returned
  - Validation: Integrity validation works

- **TC-MP-015**: Validate video file integrity
  - Input: Corrupted video file
  - Expected: Error returned
  - Validation: Video integrity validation works

- **TC-MP-016**: Validate caption length
  - Input: Various caption lengths
  - Expected: Only valid lengths accepted
  - Validation: Caption length validation works

### 7. Multi-Account Management Tests

#### 7.1 Account Selection
**Test Cases:**
- **TC-MA-001**: Default to active account
  - Input: No account_id specified
  - Expected: Uses active account
  - Validation: Default account selection works

- **TC-MA-002**: Use specified account when provided
  - Input: account_id="specific_account"
  - Expected: Uses specified account
  - Validation: Account override works

- **TC-MA-003**: Handle invalid account_id
  - Input: account_id="nonexistent"
  - Expected: Error returned
  - Validation: Account validation works

- **TC-MA-004**: Handle no active account
  - Setup: No active account configured
  - Input: No account_id specified
  - Expected: Error returned
  - Validation: No active account handling works

#### 7.2 Account Isolation
**Test Cases:**
- **TC-MA-005**: Posting limits per account
  - Setup: Account A at limit, Account B not at limit
  - Input: Post from Account B
  - Expected: Post allowed from Account B
  - Validation: Account-specific limits work

- **TC-MA-006**: Posting history per account
  - Setup: Posts from multiple accounts
  - Expected: History separated by account
  - Validation: Account-specific history works

- **TC-MA-007**: Cookies per account
  - Setup: Multiple accounts configured
  - Expected: Each account uses its own cookies
  - Validation: Account-specific authentication works

### 8. Posting Limits & History Tests

#### 8.1 Daily Posting Limits
**Test Cases:**
- **TC-LM-001**: Enforce 10 posts per day limit
  - Setup: Account with 10 posts today
  - Input: Attempt 11th post
  - Expected: Post blocked with limit error
  - Validation: Daily limit enforced

- **TC-LM-002**: Count all media types toward limit
  - Setup: Mix of photos, videos, carousels (10 total)
  - Input: Attempt any media type
  - Expected: Post blocked
  - Validation: Combined limit enforcement

- **TC-LM-003**: Reset daily counter at midnight
  - Setup: Account at limit at 23:59, wait until 00:01
  - Input: Attempt post
  - Expected: Post allowed
  - Validation: Daily reset works

- **TC-LM-004**: Track post count correctly
  - Setup: Multiple successful posts
  - Expected: Accurate post count
  - Validation: Counting accuracy

#### 8.2 Cooldown Periods
**Test Cases:**
- **TC-LM-005**: Enforce 30-minute cooldown
  - Setup: Post at 12:00, attempt at 12:15
  - Input: Attempt post during cooldown
  - Expected: Post blocked with cooldown error
  - Validation: Cooldown enforced

- **TC-LM-006**: Allow post after cooldown expires
  - Setup: Post at 12:00, attempt at 12:31
  - Input: Attempt post after cooldown
  - Expected: Post allowed
  - Validation: Cooldown expiration works

- **TC-LM-007**: Cooldown applies to all media types
  - Setup: Photo post at 12:00, attempt video at 12:15
  - Input: Attempt different media type
  - Expected: Post blocked
  - Validation: Cross-media cooldown works

#### 8.3 Posting History
**Test Cases:**
- **TC-LM-008**: Record successful post
  - Input: Successful post
  - Expected: Entry in posting history
  - Validation: Success logging works

- **TC-LM-009**: Record failed post attempt
  - Input: Failed post attempt
  - Expected: Entry in posting history with error
  - Validation: Failure logging works

- **TC-LM-010**: Include all post metadata
  - Input: Post with various features
  - Expected: Complete metadata in history
  - Validation: Complete metadata logging

- **TC-LM-011**: Retrieve posting history for account
  - Input: Account with posting history
  - Expected: Complete history returned
  - Validation: History retrieval works

- **TC-LM-012**: Filter history by media type
  - Input: Account with mixed media posts
  - Expected: Filtered history by type
  - Validation: History filtering works

- **TC-LM-013**: Filter history by date range
  - Input: Account with posts over time
  - Expected: Posts within date range
  - Validation: Date filtering works

### 9. Integration Tests

#### 9.1 Cross-Feature Integration
**Test Cases:**
- **TC-IG-001**: Complete posting workflow
  - Flow: Create media → Process → Upload → Record history
  - Expected: All steps complete successfully
  - Validation: End-to-end workflow works

- **TC-IG-002**: Multi-media posting sequence
  - Setup: Post photo, then video, then carousel
  - Expected: All posts successful with limits respected
  - Validation: Sequential posting works

- **TC-IG-003**: Cross-posting integration
  - Setup: Enable Facebook and Threads cross-post
  - Expected: Post appears on all platforms
  - Validation: Cross-platform integration works

- **TC-IG-004**: Scheduling integration
  - Setup: Schedule multiple posts for different times
  - Expected: All posts scheduled correctly
  - Validation: Scheduling system integration works

#### 9.2 Error Recovery Integration
**Test Cases:**
- **TC-IG-005**: Recover from processing failure
  - Setup: Media processing fails
  - Expected: Error logged, system remains functional
  - Validation: Graceful failure handling

- **TC-IG-006**: Recover from upload failure
  - Setup: Upload fails after processing
  - Expected: Error logged, processed media cleaned up
  - Validation: Cleanup after failure works

- **TC-IG-007**: Retry after transient failure
  - Setup: Transient network error
  - Expected: Retry succeeds
  - Validation: Retry logic works

#### 9.3 Multi-Account Integration
**Test Cases:**
- **TC-IG-008**: Switch accounts between posts
  - Setup: Post from Account A, then Account B
  - Expected: Both posts successful
  - Validation: Account switching works

- **TC-IG-009**: Concurrent posting from different accounts
  - Setup: Simultaneous posts from Account A and B
  - Expected: Both posts successful
  - Validation: Concurrent multi-account works

### 10. Performance Tests

#### 10.1 Processing Performance
**Test Cases:**
- **TC-PF-001**: Image processing speed
  - Input: Standard 1080p image
  - Expected: Processing completes in < 5 seconds
  - Validation: Processing performance acceptable

- **TC-PF-002**: Video processing speed
  - Input: Standard 60-second video
  - Expected: Processing completes in < 30 seconds
  - Validation: Video processing performance acceptable

- **TC-PF-003**: Carousel processing speed
  - Input: 10-image carousel
  - Expected: Processing completes in < 30 seconds
  - Validation: Carousel processing performance acceptable

#### 10.2 Upload Performance
**Test Cases:**
- **TC-PF-004**: Photo upload speed
  - Input: Standard photo
  - Expected: Upload completes in < 10 seconds
  - Validation: Photo upload performance acceptable

- **TC-PF-005**: Video upload speed
  - Input: Standard video
  - Expected: Upload completes in < 30 seconds
  - Validation: Video upload performance acceptable

- **TC-PF-006**: Carousel upload speed
  - Input: 5-image carousel
  - Expected: Upload completes in < 20 seconds
  - Validation: Carousel upload performance acceptable

#### 10.3 System Performance
**Test Cases:**
- **TC-PF-007**: Handle 100 posting history entries
  - Setup: Account with 100 posts
  - Expected: History retrieval in < 2 seconds
  - Validation: History scaling acceptable

- **TC-PF-008**: Handle 1000 posting history entries
  - Setup: Account with 1000 posts
  - Expected: History retrieval in < 5 seconds
  - Validation: Large history scaling acceptable

### 11. Security Tests

#### 11.1 Input Validation
**Test Cases:**
- **TC-SC-001**: Path traversal in file paths
  - Input: image_path="../../../etc/passwd"
  - Expected: Error returned
  - Validation: Path traversal prevented

- **TC-SC-002**: Command injection in captions
  - Input: caption="'; rm -rf /"
  - Expected: Input sanitized or rejected
  - Validation: Command injection prevented

- **TC-SC-003**: XSS in captions and templates
  - Input: caption="<script>alert('xss')</script>"
  - Expected: Input sanitized
  - Validation: XSS prevented

- **TC-SC-004**: SQL injection in extra_data
  - Input: extra_data={"field": "'; DROP TABLE--"}
  - Expected: Input sanitized or rejected
  - Validation: SQL injection prevented

#### 11.2 File Security
**Test Cases:**
- **TC-SC-005**: Malicious file upload
  - Input: Executable file with image extension
  - Expected: File rejected or sanitized
  - Validation: Malicious file prevention

- **TC-SC-006**: File size limits
  - Input: Extremely large file
  - Expected: Error returned
  - Validation: File size limits enforced

- **TC-SC-007**: File type validation
  - Input: File with false extension
  - Expected: File rejected based on content
  - Validation: Content-based validation works

#### 11.3 Authorization
**Test Cases:**
- **TC-SC-008**: Cross-account posting prevention
  - Setup: Account A tries to post as Account B
  - Expected: Access denied
  - Validation: Account isolation enforced

- **TC-SC-009**: Invalid session handling
  - Setup: Expired session cookies
  - Expected: Authentication error
  - Validation: Session validation works

- **TC-SC-010**: Rate limiting abuse prevention
  - Setup: Rapid successive posting attempts
  - Expected: Rate limited after threshold
  - Validation: Rate limiting works

### 12. Error Handling Tests

#### 12.1 Instagram API Errors
**Test Cases:**
- **TC-EH-001**: Handle ChallengeRequired error
  - Setup: Simulate challenge required
  - Expected: Appropriate error message
  - Validation: Challenge error handling works

- **TC-EH-002**: Handle LoginRequired error
  - Setup: Simulate login required
  - Expected: Appropriate error message
  - Validation: Login error handling works

- **TC-EH-003**: Handle FeedbackRequired error
  - Setup: Simulate feedback required
  - Expected: Appropriate error message
  - Validation: Feedback error handling works

- **TC-EH-004**: Handle SentryBlock error
  - Setup: Simulate sentry block
  - Expected: Appropriate error message
  - Validation: Block error handling works

#### 12.2 Network Errors
**Test Cases:**
- **TC-EH-005**: Handle network timeout
  - Setup: Simulate network timeout
  - Expected: Timeout error returned
  - Validation: Timeout handling works

- **TC-EH-006**: Handle connection failure
  - Setup: Simulate connection failure
  - Expected: Connection error returned
  - Validation: Connection error handling works

- **TC-EH-007**: Handle DNS resolution failure
  - Setup: Simulate DNS failure
  - Expected: DNS error returned
  - Validation: DNS error handling works

#### 12.3 System Errors
**Test Cases:**
- **TC-EH-008**: Handle disk space exhaustion
  - Setup: Simulate full disk
  - Expected: Disk space error returned
  - Validation: Disk space handling works

- **TC-EH-009**: Handle memory exhaustion
  - Setup: Simulate out of memory
  - Expected: Memory error returned
  - Validation: Memory error handling works

- **TC-EH-010**: Handle file permission errors
  - Setup: Simulate permission denied
  - Expected: Permission error returned
  - Validation: Permission error handling works

## Test Execution Procedure

### Prerequisites
1. Ensure test environment is set up with valid Instagram account
2. Prepare test media files (images, videos)
3. Obtain valid location IDs for testing
4. Coordinate with test users for tagging tests
5. Backup existing posting configurations and history

### Execution Order
1. Run Basic Upload Tests (1.1-5.1)
2. Run Advanced Features Tests (1.2-5.3)
3. Run Multi-Account Tests (1.3-5.4, 7.1-7.2)
4. Run Limits & History Tests (1.4-5.4, 8.1-8.3)
5. Run Error Handling Tests (1.5-5.5, 12.1-12.3)
6. Run Media Processing Tests (6.1-6.3)
7. Run Integration Tests (9.1-9.3)
8. Run Performance Tests (10.1-10.3)
9. Run Security Tests (11.1-11.3)

### Test Data Cleanup
- Delete all test posts after testing
- Clean up test media files
- Reset posting limits and counters
- Restore original configurations

## Success Criteria
- **Functional**: 95%+ of test cases pass
- **Performance**: All performance tests meet time thresholds
- **Security**: All security tests show no vulnerabilities
- **Integration**: All integration workflows complete successfully
- **Reliability**: No system crashes or data corruption during testing
- **Multi-Account**: Account isolation and switching work perfectly

## Test Reporting
Document results for each test case including:
- Test case ID and description
- Input parameters
- Expected vs actual results
- Pass/fail status
- Screenshots/logs where applicable
- Post URLs for verification
- Bug reports for failed tests

## Known Limitations
- Tests require valid Instagram session cookies
- Some tests require coordination with other users
- Rate limiting may affect test execution speed
- Instagram API changes may affect test reliability
- Cross-posting tests require linked Facebook/Threads accounts
- Location tagging requires valid Instagram location IDs
- Video processing tests require sufficient system resources