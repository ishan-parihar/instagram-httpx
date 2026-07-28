"""
Instagram user profile scraping tools.

Provides tools for fetching user profiles, posts, reels,
stories, and highlights via innerText extraction.
"""

import logging
from typing import Any

from fastmcp import Context, FastMCP
from fastmcp.dependencies import CurrentContext

from instagram_mcp_server.callbacks import MCPContextProgressCallback
from instagram_mcp_server.constants import TOOL_TIMEOUT_SECONDS
from instagram_mcp_server.dependencies import get_ready_extractor
from instagram_mcp_server.tools._guard import tool_guard
from instagram_mcp_server.scraping import parse_user_sections

import tempfile
from pathlib import Path

from instagram_mcp_server.media import (
    download_media as _download_media,
    extract_frames as _extract_frames,
    get_video_duration,
)

logger = logging.getLogger(__name__)


def register_user_tools(mcp: FastMCP) -> None:
    """Register all user-related tools with the MCP server."""

    @mcp.tool(
        timeout=TOOL_TIMEOUT_SECONDS,
        title="Get User Profile",
        annotations={"readOnlyHint": True, "openWorldHint": True},
        tags={"user", "scraping"},
    )
    @tool_guard("get_user_profile")
    async def get_user_profile(
        username: str,
        sections: str | None = None,
        account_id: str | None = None,
        ctx: Context = CurrentContext(),
    ) -> dict[str, Any]:
        """
        Get an Instagram user's profile.

        Args:
            username: Instagram username (e.g., "instagram", "natgeo")
            sections: Comma-separated list of extra sections to scrape.
                The main profile page is always included.
                Available sections: posts, reels, tagged, followers, following
                Examples: "posts,reels", "tagged", "followers,following"
                Default (None) scrapes only the main profile page.
            account_id: Optional account ID to use for the request

        Returns:
            Dict with url, sections (name -> raw text), and optional references.
            Sections may be absent if extraction yielded no content for that page.
            Includes unknown_sections list when unrecognised names are passed.
            The LLM should parse the raw text in each section.
        """
        extractor = await get_ready_extractor(ctx, tool_name="get_user_profile", account_id=account_id)
        requested, unknown = parse_user_sections(sections)

        logger.info(
            "Scraping user profile: %s (sections=%s)",
            username,
            sections,
        )

        cb = MCPContextProgressCallback(ctx)
        result = await extractor.scrape_user(username, requested, callbacks=cb)

        if unknown:
            result["unknown_sections"] = unknown

        return result

    @mcp.tool(
        timeout=TOOL_TIMEOUT_SECONDS,
        title="Get User Posts",
        annotations={"readOnlyHint": True, "openWorldHint": True},
        tags={"user", "scraping"},
    )
    @tool_guard("get_user_posts")
    async def get_user_posts(
        username: str,
        max_posts: int = 50,
        download_media: bool = False,
        extract_frames: bool = False,
        account_id: str | None = None,
        ctx: Context = CurrentContext(),
    ) -> dict[str, Any]:
        """
        Get an Instagram user's posts with structured data.

        Args:
            username: Instagram username (e.g., "instagram", "natgeo")
            max_posts: Maximum number of posts to retrieve (default 50)
            download_media: Download images/videos to local temp directory
                (default: False). When True, returns downloaded_media with paths.
            extract_frames: Extract video frames at 1 FPS to local temp directory
                (default: False). When True, returns frame_dirs with frame paths.
            account_id: Optional account ID to use for the request

        Returns:
            Dict with url, posts list, total_posts count, sections, and references.
            Each post has: id, shortcode, url, thumbnail_url, media_type.
        """
        extractor = await get_ready_extractor(ctx, tool_name="get_user_posts", account_id=account_id)

        logger.info(
            "Scraping user posts: %s (max_posts=%d)",
            username,
            max_posts,
        )

        cb = MCPContextProgressCallback(ctx)
        result = await extractor.scrape_user_posts(
            username, max_posts, callbacks=cb
        )

        # --- Media download / frame extraction ---
        download_dir = None
        downloaded_media = []
        frame_dirs = []

        if download_media or extract_frames:
            download_dir = tempfile.mkdtemp(prefix="ig_posts_")
            posts_data = result.get("posts", [])
            total = len(posts_data)

            for idx, post in enumerate(posts_data):
                post_id = post.get("id", str(idx))
                item_dir = Path(download_dir) / f"post_{post_id}"
                item_dir.mkdir(parents=True, exist_ok=True)

                await ctx.report_progress(
                    progress=int((idx / total) * 100),
                    total=100,
                    message=f"Processing media for post {idx + 1}/{total}...",
                )

                # Download thumbnail (CDN image - available for all media types)
                if download_media:
                    thumb_url = post.get("thumbnail", "")
                    if thumb_url:
                        thumb_path = item_dir / "thumbnail.jpg"
                        if await _download_media(
                            thumb_url, thumb_path, extractor._cookies
                        ):
                            downloaded_media.append({
                                "post_id": post_id,
                                "shortcode": post.get("shortcode", ""),
                                "type": "thumbnail",
                                "path": str(thumb_path),
                            })

                    # For reels/videos (media_type 2), also attempt full video download when extracting frames
                    if post.get("media_type") in (2,) and (extract_frames):
                        try:
                            details = await extractor.get_post_details(
                                post.get("url", "")
                            )
                            pd = details.get("post_details", {})
                            video_url = pd.get("video_url", "")
                            if video_url:
                                video_path = item_dir / "video.mp4"
                                if await _download_media(
                                    video_url, video_path, extractor._cookies
                                ):
                                    if download_media:
                                        downloaded_media.append({
                                            "post_id": post_id,
                                            "shortcode": post.get("shortcode", ""),
                                            "type": "video",
                                            "path": str(video_path),
                                        })
                                    # Extract frames from video
                                    if extract_frames:
                                        frames_dir = item_dir / "frames"
                                        frames = _extract_frames(
                                            video_path,
                                            frames_dir,
                                            fps=1.0,
                                        )
                                        if frames:
                                            frame_dirs.append({
                                                "post_id": post_id,
                                                "shortcode": post.get("shortcode", ""),
                                                "frame_dir": str(frames_dir),
                                                "frames": [str(f) for f in frames],
                                                "fps": 1.0,
                                                "total_frames": len(frames),
                                                "video_duration": get_video_duration(video_path),
                                            })
                        except Exception as e:
                            logger.warning("Frame extraction failed for %s: %s", post_id, e)

                    # For carousel posts (media_type 8), download carousel children
                    carousel = post.get("carousel_media", [])
                    for ci, cm in enumerate(carousel):
                        thumb_url = cm.get("thumbnail", "")
                        if thumb_url:
                            car_path = item_dir / f"carousel_{ci}.jpg"
                            if await _download_media(
                                thumb_url, car_path, extractor._cookies
                            ):
                                downloaded_media.append({
                                    "post_id": post_id,
                                    "shortcode": post.get("shortcode", ""),
                                    "type": f"carousel_{ci}",
                                    "path": str(car_path),
                                })

        if downloaded_media or frame_dirs:
            result["download_dir"] = download_dir
            if downloaded_media:
                result["downloaded_media"] = downloaded_media
            if frame_dirs:
                result["frame_dirs"] = frame_dirs

        return result

    @mcp.tool(
        timeout=TOOL_TIMEOUT_SECONDS,
        title="Get User Reels",
        annotations={"readOnlyHint": True, "openWorldHint": True},
        tags={"user", "scraping"},
    )
    @tool_guard("get_user_reels")
    async def get_user_reels(
        username: str,
        max_reels: int = 50,
        download_media: bool = False,
        extract_frames: bool = False,
        account_id: str | None = None,
        ctx: Context = CurrentContext(),
    ) -> dict[str, Any]:
        """
        Get an Instagram user's reels with structured data.

        Returns reel IDs, URLs, thumbnails, and view counts from the grid page
        without navigating to individual reels (avoids N+1 rate limiting).

        Args:
            username: Instagram username (e.g., "instagram", "natgeo")
            max_reels: Maximum number of reels to retrieve (default 50)
            download_media: Download images/videos to local temp directory
                (default: False). When True, returns downloaded_media with paths.
            extract_frames: Extract video frames at adaptive FPS to local temp directory
                (default: False). When True, returns frame_dirs with frame paths.
            account_id: Optional account ID to use for the request

        Returns:
            Dict with url, reels list, total_reels count, sections, and references.
            Each reel has: id, shortcode, url, thumbnail_url, view_count_text, media_type.
            Use `get_post_details` on individual reel URLs for full engagement data.
        """
        extractor = await get_ready_extractor(ctx, tool_name="get_user_reels", account_id=account_id)

        logger.info(
            "Scraping user reels: %s (max_reels=%d)",
            username,
            max_reels,
        )

        cb = MCPContextProgressCallback(ctx)
        result = await extractor.scrape_user_reels(
            username, max_reels, callbacks=cb
        )

        # --- Media download / frame extraction ---
        download_dir = None
        downloaded_media = []
        frame_dirs = []

        if download_media or extract_frames:
            download_dir = tempfile.mkdtemp(prefix="ig_reels_")
            reels_data = result.get("reels", [])
            total = len(reels_data)

            for idx, reel in enumerate(reels_data):
                reel_id = reel.get("id", str(idx))
                item_dir = Path(download_dir) / f"reel_{reel_id}"
                item_dir.mkdir(parents=True, exist_ok=True)

                await ctx.report_progress(
                    progress=int((idx / total) * 100),
                    total=100,
                    message=f"Processing reel {idx + 1}/{total}...",
                )

                # Download thumbnail
                thumb_url = reel.get("thumbnail", "")
                if download_media and thumb_url:
                    thumb_path = item_dir / "thumbnail.jpg"
                    if await _download_media(thumb_url, thumb_path, extractor._cookies):
                        downloaded_media.append({
                            "reel_id": reel_id,
                            "shortcode": reel.get("shortcode", ""),
                            "type": "thumbnail",
                            "path": str(thumb_path),
                        })

                # For full video: needed for frames or if download_media wants the full video
                if extract_frames or (download_media and reel.get("play_count", 0) > 0 and thumb_url):
                    try:
                        details = await extractor.get_post_details(reel.get("url", ""))
                        pd = details.get("post_details", {})
                        video_url = pd.get("video_url", "")
                        if not video_url:
                            continue

                        video_path = item_dir / "video.mp4"
                        if await _download_media(video_url, video_path, extractor._cookies):
                            if download_media:
                                downloaded_media.append({
                                    "reel_id": reel_id,
                                    "shortcode": reel.get("shortcode", ""),
                                    "type": "video",
                                    "path": str(video_path),
                                })

                            if extract_frames:
                                frames_dir = item_dir / "frames"
                                duration = get_video_duration(video_path)
                                # Adaptive FPS: ensure we get at least 3 frames but no more than 60
                                adaptive_fps = max(0.2, min(1.0, 60.0 / duration)) if duration > 0 else 1.0
                                frames = _extract_frames(
                                    video_path, frames_dir, fps=adaptive_fps, max_frames=60,
                                )
                                if frames:
                                    frame_dirs.append({
                                        "reel_id": reel_id,
                                        "shortcode": reel.get("shortcode", ""),
                                        "frame_dir": str(frames_dir),
                                        "frames": [str(f) for f in frames],
                                        "fps": adaptive_fps,
                                        "total_frames": len(frames),
                                        "video_duration": duration,
                                    })
                    except Exception as e:
                        logger.warning("Video processing failed for reel %s: %s", reel_id, e)

        if downloaded_media or frame_dirs:
            result["download_dir"] = download_dir
            if downloaded_media:
                result["downloaded_media"] = downloaded_media
            if frame_dirs:
                result["frame_dirs"] = frame_dirs

        return result

    @mcp.tool(
        timeout=TOOL_TIMEOUT_SECONDS,
        title="Get User Stories",
        annotations={"readOnlyHint": True, "openWorldHint": True},
        tags={"user", "scraping"},
    )
    @tool_guard("get_user_stories")
    async def get_user_stories(
        username: str,
        download_media: bool = False,
        extract_frames: bool = False,
        account_id: str | None = None,
        ctx: Context = CurrentContext(),
    ) -> dict[str, Any]:
        """
        Get an Instagram user's active stories.

        Args:
            username: Instagram username (e.g., "instagram", "natgeo")
            download_media: Download images/videos to local temp directory
                (default: False). When True, returns downloaded_media with paths.
            extract_frames: Extract video frames at adaptive FPS to local temp directory
                (default: False). When True, returns frame_dirs with frame paths.
            account_id: Optional account ID to use for the request

        Returns:
            Dict with url and stories list, where each story has:
            media_url, timestamp, expires_at.
        """
        extractor = await get_ready_extractor(ctx, tool_name="get_user_stories", account_id=account_id)

        logger.info("Scraping user stories: %s", username)

        await ctx.report_progress(
            progress=0, total=100, message="Fetching active stories"
        )

        result = await extractor.scrape_user_stories(username)

        # --- Media download / frame extraction ---
        download_dir = None
        downloaded_media = []
        frame_dirs = []

        if download_media or extract_frames:
            download_dir = tempfile.mkdtemp(prefix="ig_stories_")
            stories_data = result.get("stories", [])
            total = len(stories_data)

            for idx, story in enumerate(stories_data):
                story_id = story.get("id", str(idx))
                item_dir = Path(download_dir) / f"story_{story_id}"
                item_dir.mkdir(parents=True, exist_ok=True)

                await ctx.report_progress(
                    progress=int((idx / total) * 100),
                    total=100,
                    message=f"Processing story {idx + 1}/{total}...",
                )

                mt = story.get("media_type", 1)

                # Download image for all stories
                if download_media:
                    img_url = story.get("url", "")
                    if img_url:
                        img_path = item_dir / "image.jpg"
                        if await _download_media(img_url, img_path, extractor._cookies):
                            downloaded_media.append({
                                "story_id": story_id,
                                "type": "image",
                                "path": str(img_path),
                            })

                # Handle video stories
                if mt == 2:
                    video_url = story.get("video_url", "")
                    if video_url:
                        video_path = item_dir / "video.mp4"
                        if await _download_media(video_url, video_path, extractor._cookies):
                            if download_media:
                                downloaded_media.append({
                                    "story_id": story_id,
                                    "type": "video",
                                    "path": str(video_path),
                                })
                            if extract_frames:
                                frames_dir = item_dir / "frames"
                                duration = get_video_duration(video_path)
                                adaptive_fps = max(0.2, min(1.0, 60.0 / duration)) if duration > 0 else 1.0
                                frames = _extract_frames(
                                    video_path, frames_dir, fps=adaptive_fps, max_frames=30,
                                )
                                if frames:
                                    frame_dirs.append({
                                        "story_id": story_id,
                                        "frame_dir": str(frames_dir),
                                        "frames": [str(f) for f in frames],
                                        "fps": adaptive_fps,
                                        "total_frames": len(frames),
                                        "video_duration": duration,
                                    })

        if downloaded_media or frame_dirs:
            result["download_dir"] = download_dir
            if downloaded_media:
                result["downloaded_media"] = downloaded_media
            if frame_dirs:
                result["frame_dirs"] = frame_dirs

        await ctx.report_progress(progress=100, total=100, message="Complete")

        return result

    @mcp.tool(
        timeout=TOOL_TIMEOUT_SECONDS,
        title="Get User Highlights",
        annotations={"readOnlyHint": True, "openWorldHint": True},
        tags={"user", "scraping"},
    )
    @tool_guard("get_user_highlights")
    async def get_user_highlights(
        username: str,
        ctx: Context = CurrentContext(),
    ) -> dict[str, Any]:
        """
        Get an Instagram user's story highlights.

        Args:
            username: Instagram username (e.g., "instagram", "natgeo")

        Returns:
            Dict with url and highlights list, where each highlight has:
            title, cover_url, highlight_id.
        """
        extractor = await get_ready_extractor(ctx, tool_name="get_user_highlights")

        logger.info("Scraping user highlights: %s", username)

        await ctx.report_progress(
            progress=0, total=100, message="Extracting story highlights"
        )

        result = await extractor.scrape_user_highlights(username)

        await ctx.report_progress(progress=100, total=100, message="Complete")

        return result
