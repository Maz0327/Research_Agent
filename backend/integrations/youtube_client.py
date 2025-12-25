"""YouTube Data API v3 client for deterministic channel upload enumeration."""
import re
from datetime import datetime, timezone
from typing import Optional

import httpx
from loguru import logger
from pydantic import BaseModel

from backend.config import require_youtube, MissingRequiredSettingError
from backend.models.job_config import JobConfig
from backend.utils.error_handling import sanitize_error_message

# Constants
YOUTUBE_API_TIMEOUT = 30.0  # seconds
YOUTUBE_API_SHORT_TIMEOUT = 10.0  # seconds for quick requests
MAX_VIDEOS_PER_REQUEST = 50  # YouTube API limit


class VideoItem(BaseModel):
    """YouTube video item with all relevant metadata."""
    video_id: str
    title: str
    channel_id: str
    channel_title: str
    published_at: datetime
    duration_seconds: Optional[int] = None
    url: str = ""  # Will be set in __init__ or via field default
    is_livestream: bool = False
    is_short: bool = False
    
    def __init__(self, **data):
        super().__init__(**data)
        # Generate URL if not provided
        if not self.url:
            self.url = f"https://www.youtube.com/watch?v={self.video_id}"


def _resolve_channel_id(channel_handle_or_url: str, api_key: str) -> Optional[str]:
    """
    Resolve channel handle/URL to channel ID.
    
    Supports:
    - Channel ID (starts with UC): returns as-is
    - Handle (starts with @): resolves via API
    - Full URL: extracts handle/ID and resolves
    
    Args:
        channel_handle_or_url: Channel handle (e.g., "@candaceowens"), URL, or channel ID
        api_key: YouTube API key
        
    Returns:
        Channel ID (UC...) or None if resolution fails
    """
    # If it's already a channel ID (starts with UC), return it
    if channel_handle_or_url.startswith("UC") and len(channel_handle_or_url) == 24:
        return channel_handle_or_url
    
    # Extract handle from URL if needed
    handle = channel_handle_or_url
    if "youtube.com" in handle:
        # Extract from URL patterns
        url_patterns = [
            r'youtube\.com/@([A-Za-z0-9_-]+)',
            r'youtube\.com/channel/(UC[a-zA-Z0-9_-]{22})',
            r'youtube\.com/c/([A-Za-z0-9_-]+)',
            r'youtube\.com/user/([A-Za-z0-9_-]+)',
        ]
        for pattern in url_patterns:
            match = re.search(pattern, handle, re.IGNORECASE)
            if match:
                extracted = match.group(1)
                if extracted.startswith("UC"):
                    return extracted  # Already a channel ID
                handle = f"@{extracted}"
                break
    
    # Ensure handle starts with @
    if not handle.startswith("@"):
        handle = f"@{handle}"
    
    # Resolve handle to channel ID via API
    try:
        url = "https://www.googleapis.com/youtube/v3/channels"
        params = {
            "part": "id",
            "forHandle": handle.lstrip("@"),  # API expects handle without @
            "key": api_key,
        }
        
        with httpx.Client(timeout=YOUTUBE_API_SHORT_TIMEOUT) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
        
        items = data.get("items", [])
        if items and "id" in items[0]:
            channel_id = items[0]["id"]
            logger.info(f"Resolved {channel_handle_or_url} to channel ID: {channel_id}")
            return channel_id
        
        logger.warning(f"Could not resolve channel handle: {handle}")
        return None
    
    except Exception as e:
        sanitized_error = sanitize_error_message(e, include_type=False)
        logger.error(f"Error resolving channel {channel_handle_or_url}: {sanitized_error}")
        return None


def _parse_duration_iso8601(duration: str) -> Optional[int]:
    """
    Parse ISO 8601 duration to seconds.
    
    Examples:
        PT1H2M10S -> 3730
        PT15M30S -> 930
        PT1M -> 60
        PT30S -> 30
    """
    if not duration or not duration.startswith("PT"):
        return None
    
    duration = duration[2:]  # Remove "PT" prefix
    
    hours = 0
    minutes = 0
    seconds = 0
    
    # Match hours
    h_match = re.search(r'(\d+)H', duration)
    if h_match:
        hours = int(h_match.group(1))
    
    # Match minutes
    m_match = re.search(r'(\d+)M', duration)
    if m_match:
        minutes = int(m_match.group(1))
    
    # Match seconds
    s_match = re.search(r'(\d+)S', duration)
    if s_match:
        seconds = int(s_match.group(1))
    
    return hours * 3600 + minutes * 60 + seconds


def _get_channel_uploads(
    channel_id: str,
    api_key: str,
    max_results: int = 50,
    published_after: Optional[datetime] = None,
    published_before: Optional[datetime] = None,
    include_livestreams: bool = False,
    exclude_shorts: bool = True,
) -> list[VideoItem]:
    """
    Get channel uploads deterministically (not search-based).
    
    Uses search API with channelId filter to enumerate uploads.
    
    Args:
        channel_id: YouTube channel ID (UC...)
        api_key: YouTube API key
        max_results: Maximum number of videos to fetch
        published_after: Filter videos published after this date
        published_before: Filter videos published before this date
        include_livestreams: Whether to include livestreams
        exclude_shorts: Whether to exclude YouTube Shorts (videos < 60 seconds)
        
    Returns:
        List of VideoItem objects
    """
    videos = []
    
    # Build search parameters
    params = {
        "part": "snippet",
        "channelId": channel_id,
        "type": "video",
        "order": "date",  # Deterministic: chronological order
        "maxResults": min(max_results, MAX_VIDEOS_PER_REQUEST),
        "key": api_key,
    }
    
    # Add date filters
    if published_after:
        params["publishedAfter"] = published_after.isoformat() + "Z"
    if published_before:
        params["publishedBefore"] = published_before.isoformat() + "Z"
    
    try:
        with httpx.Client(timeout=YOUTUBE_API_TIMEOUT) as client:
            # Get first page
            url = "https://www.googleapis.com/youtube/v3/search"
            response = client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            items = data.get("items", [])
            video_ids = [item["id"]["videoId"] for item in items if "videoId" in item.get("id", {})]
            
            # Fetch detailed video information (duration, live status, etc.)
            if video_ids:
                videos_details = _get_videos_details(video_ids, api_key)
                
                # Merge search results with details
                for item in items:
                    video_id = item.get("id", {}).get("videoId")
                    if not video_id:
                        continue
                    
                    snippet = item.get("snippet", {})
                    details = videos_details.get(video_id, {})
                    content_details = details.get("contentDetails", {})
                    details.get("status", {})
                    
                    # Parse published date
                    published_str = snippet.get("publishedAt", "")
                    try:
                        published_at = datetime.fromisoformat(published_str.replace("Z", "+00:00"))
                    except (ValueError, AttributeError):
                        logger.warning(f"Could not parse published date: {published_str}")
                        continue
                    
                    # Get duration
                    duration_str = content_details.get("duration", "")
                    duration_seconds = _parse_duration_iso8601(duration_str)
                    
                    # Check if livestream
                    live_broadcast_content = snippet.get("liveBroadcastContent", "none")
                    is_livestream = live_broadcast_content == "live" or live_broadcast_content == "upcoming"
                    
                    # Check if short (typically < 60 seconds)
                    is_short = False
                    if duration_seconds:
                        is_short = duration_seconds < 60
                    
                    # Apply filters
                    if is_livestream and not include_livestreams:
                        continue
                    
                    if is_short and exclude_shorts:
                        continue
                    
                    video = VideoItem(
                        video_id=video_id,
                        title=snippet.get("title", ""),
                        channel_id=channel_id,
                        channel_title=snippet.get("channelTitle", ""),
                        published_at=published_at,
                        duration_seconds=duration_seconds,
                        is_livestream=is_livestream,
                        is_short=is_short,
                    )
                    videos.append(video)
        
        # Sort by published date (most recent first)
        videos.sort(key=lambda v: v.published_at, reverse=True)
        
        # Limit to max_results
        return videos[:max_results]
    
    except Exception as e:
        sanitized_error = sanitize_error_message(e, include_type=False)
        logger.error(f"Error fetching channel uploads for {channel_id}: {sanitized_error}")
        return []


def _get_videos_details(video_ids: list[str], api_key: str) -> dict[str, dict]:
    """
    Fetch detailed information for multiple videos.
    
    Args:
        video_ids: List of video IDs
        api_key: YouTube API key
        
    Returns:
        Dict mapping video_id to video details
    """
    # YouTube API allows up to MAX_VIDEOS_PER_REQUEST IDs per request
    batch_size = MAX_VIDEOS_PER_REQUEST
    all_details = {}
    
    for i in range(0, len(video_ids), batch_size):
        batch = video_ids[i:i + batch_size]
        
        try:
            url = "https://www.googleapis.com/youtube/v3/videos"
            params = {
                "part": "contentDetails,status",
                "id": ",".join(batch),
                "key": api_key,
            }
            
            with httpx.Client(timeout=YOUTUBE_API_SHORT_TIMEOUT) as client:
                response = client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            for item in data.get("items", []):
                video_id = item.get("id")
                if video_id:
                    all_details[video_id] = item
        
        except Exception as e:
            logger.warning(f"Error fetching video details for batch: {e}")
            continue
    
    return all_details


def enumerate_channel_uploads(job: JobConfig) -> dict:
    """
    Enumerate uploads from channels specified in job config.
    
    Args:
        job: JobConfig with youtube configuration
        
    Returns:
        Dict with 'videos' (list of VideoItem) and 'youtube_index_md' (markdown table)
    """
    try:
        settings = require_youtube()
    except MissingRequiredSettingError:
        logger.warning("YouTube API key not configured. Returning empty result.")
        return {
            "videos": [],
            "youtube_index_md": "# YouTube Index\n\n*YouTube API key required.*",
        }
    
    all_videos: list[VideoItem] = []
    
    # Resolve channel IDs
    resolved_channels: dict[str, str] = {}  # channel_id -> channel_title
    
    for channel_spec in job.youtube.channels:
        channel_id = _resolve_channel_id(channel_spec, settings.youtube_api_key)
        if channel_id:
            resolved_channels[channel_id] = channel_id  # Will update with title later
        else:
            logger.warning(f"Could not resolve channel: {channel_spec}")
    
    if not resolved_channels:
        logger.warning("No valid channels resolved. Returning empty result.")
        return {
            "videos": [],
            "youtube_index_md": f"# YouTube Index\n\n**Topic:** {job.topic}\n\n*No valid channels found.*",
        }
    
    # Determine time window
    published_after = None
    published_before = None
    
    if job.time_window.start:
        published_after = datetime.combine(
            job.time_window.start,
            datetime.min.time(),
            tzinfo=timezone.utc,
        )
    
    if job.time_window.end:
        published_before = datetime.combine(
            job.time_window.end,
            datetime.max.time(),
            tzinfo=timezone.utc,
        )
    else:
        # Default end to now
        published_before = datetime.now(timezone.utc)
    
    # Fetch uploads for each channel
    for channel_id in resolved_channels.keys():
        videos = _get_channel_uploads(
            channel_id=channel_id,
            api_key=settings.youtube_api_key,
            max_results=job.youtube.max_videos,
            published_after=published_after,
            published_before=published_before,
            include_livestreams=job.youtube.include_livestreams,
            exclude_shorts=job.youtube.exclude_shorts,
        )
        
        all_videos.extend(videos)
        
        # Update channel title from first video
        if videos and not resolved_channels[channel_id].startswith("UC"):
            resolved_channels[channel_id] = videos[0].channel_title
    
    # Sort all videos by published date (most recent first)
    all_videos.sort(key=lambda v: v.published_at, reverse=True)
    
    # Generate markdown index
    youtube_index_md = _generate_youtube_index_md(job, all_videos, resolved_channels)
    
    return {
        "videos": all_videos,
        "youtube_index_md": youtube_index_md,
    }


def _generate_youtube_index_md(
    job: JobConfig,
    videos: list[VideoItem],
    channel_map: dict[str, str],
) -> str:
    """
    Generate markdown table index of YouTube videos.
    
    Args:
        job: JobConfig
        videos: List of VideoItem objects
        channel_map: Dict mapping channel_id to channel_title
        
    Returns:
        Markdown string with table
    """
    lines = [
        "# YouTube Index",
        "",
        f"**Topic:** {job.topic}",
        f"**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
        f"**Total Videos:** {len(videos)}",
        "",
    ]
    
    if not videos:
        lines.append("*No videos found.*")
        return "\n".join(lines)
    
    # Group by channel
    videos_by_channel: dict[str, list[VideoItem]] = {}
    for video in videos:
        if video.channel_id not in videos_by_channel:
            videos_by_channel[video.channel_id] = []
        videos_by_channel[video.channel_id].append(video)
    
    for channel_id, channel_videos in videos_by_channel.items():
        channel_title = channel_map.get(channel_id, channel_videos[0].channel_title if channel_videos else channel_id)
        
        lines.append(f"## {channel_title}")
        lines.append("")
        lines.append("| Published | Title | Duration | Type |")
        lines.append("|-----------|-------|----------|------|")
        
        for video in channel_videos:
            # Format date
            date_str = video.published_at.strftime("%Y-%m-%d")
            
            # Format duration
            if video.duration_seconds:
                hours = video.duration_seconds // 3600
                minutes = (video.duration_seconds % 3600) // 60
                seconds = video.duration_seconds % 60
                if hours > 0:
                    duration_str = f"{hours}:{minutes:02d}:{seconds:02d}"
                else:
                    duration_str = f"{minutes}:{seconds:02d}"
            else:
                duration_str = "?"
            
            # Determine type
            type_str = "Livestream" if video.is_livestream else ("Short" if video.is_short else "Video")
            
            # Create markdown link
            title_link = f"[{video.title}]({video.url})"
            
            lines.append(f"| {date_str} | {title_link} | {duration_str} | {type_str} |")
        
        lines.append("")
    
    return "\n".join(lines)

