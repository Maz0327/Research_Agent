"""YouTube Data API v3 integration."""
from typing import Optional

import httpx
from loguru import logger
from pydantic import BaseModel

from backend.config import require_youtube


class YouTubeVideo(BaseModel):
    """YouTube video model."""
    
    video_id: str
    title: str
    channel_title: Optional[str] = None
    published_at: Optional[str] = None


OEMBED_ENDPOINT = "https://www.youtube.com/oembed"


def fetch_oembed_metadata(video_url: str, timeout: float = 10.0) -> Optional[dict]:
    """Fetch a YouTube video's title and channel via oEmbed.

    oEmbed needs no API key and no quota, which makes it the right fallback
    when Supadata metadata is unavailable (rate limited, or the key is out of
    credits). Without it, source packages carry `creator=None` and documents
    cannot attribute anything by name.

    Args:
        video_url: Full YouTube watch URL.
        timeout: Request timeout in seconds.

    Returns:
        Dict with `title` and `creator`, or None when the lookup fails (private
        or deleted videos included).
    """
    try:
        response = httpx.get(
            OEMBED_ENDPOINT,
            params={"url": video_url, "format": "json"},
            timeout=timeout,
            follow_redirects=True,
        )
        if response.status_code != 200:
            logger.debug(
                f"oEmbed returned {response.status_code} for {video_url[:60]}"
            )
            return None

        data = response.json()
    except Exception as e:
        logger.debug(f"oEmbed lookup failed for {video_url[:60]}: {e}")
        return None

    title = data.get("title")
    creator = data.get("author_name")
    if not title and not creator:
        return None

    return {"title": title, "creator": creator}


def search_youtube_videos(query: str, max_results: int = 5) -> list[YouTubeVideo]:
    """
    Search for YouTube videos using the YouTube Data API v3.
    
    Args:
        query: Search query string
        max_results: Maximum number of results to return (default: 5, max: 50)
        
    Returns:
        List of YouTubeVideo instances. Returns empty list if:
        - No API key is configured
        - API request fails
        - Response parsing fails
        
    Example:
        >>> videos = search_youtube_videos("python tutorial", max_results=3)
        >>> for video in videos:
        ...     print(f"{video.title} by {video.channel_title}")
    """
    try:
        settings = require_youtube()
    except Exception as e:
        logger.warning(f"YouTube integration not available: {e}")
        return []
    
    # Validate max_results
    if max_results < 1:
        logger.warning(f"Invalid max_results: {max_results}. Using default: 5")
        max_results = 5
    elif max_results > 50:
        logger.warning("max_results exceeds API limit (50). Clamping to 50")
        max_results = 50
    
    try:
        # YouTube Data API v3 search endpoint
        url = "https://www.googleapis.com/youtube/v3/search"
        params = {
            "part": "snippet",
            "type": "video",
            "q": query,
            "maxResults": max_results,
            "key": settings.youtube_api_key,
        }
        
        logger.info(f"Searching YouTube for: {query} (max_results={max_results})")
        
        # Make API request
        with httpx.Client(timeout=10.0) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
        
        # Parse response
        videos = []
        items = data.get("items", [])
        
        for item in items:
            try:
                snippet = item.get("snippet", {})
                video_id = item.get("id", {}).get("videoId")
                
                if not video_id:
                    logger.warning("Skipping item with missing videoId")
                    continue
                
                video = YouTubeVideo(
                    video_id=video_id,
                    title=snippet.get("title", ""),
                    channel_title=snippet.get("channelTitle"),
                    published_at=snippet.get("publishedAt"),
                )
                videos.append(video)
                
            except Exception as e:
                logger.error(f"Error parsing video item: {e}")
                continue
        
        logger.info(f"Found {len(videos)} YouTube videos for query: {query}")
        return videos
        
    except httpx.HTTPStatusError as e:
        logger.error(f"YouTube API HTTP error: {e.response.status_code} - {e.response.text}")
        return []
    except httpx.RequestError as e:
        logger.error(f"YouTube API request error: {e}")
        return []
    except KeyError as e:
        logger.error(f"Unexpected response structure from YouTube API: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error searching YouTube: {e}")
        return []

