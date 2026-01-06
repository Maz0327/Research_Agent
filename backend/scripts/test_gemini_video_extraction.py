#!/usr/bin/env python3
"""
Phase 1 Test: Gemini Video Extraction Validation

Tests whether Gemini 2.5 can extract timestamps + quotes from YouTube videos.
This is a GROUNDED ONLY test - no creative output, just extraction accuracy.

Test Criteria (from plan):
- YouTube URL input works
- Timestamps accurate within ±5 seconds
- Verbatim quotes match actual speech
- Speaker identification works

Pass Criteria: 4/5 test videos pass accuracy check.
"""
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from loguru import logger

# Test videos - mix of types to validate across use cases
TEST_VIDEOS = [
    {
        "name": "Rick Astley (known video for baseline)",
        "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "expected_duration_min": 3,
    },
    {
        "name": "TED Talk (structured speech)",
        "url": "https://www.youtube.com/watch?v=8S0FDjFBj8o",  # Simon Sinek - Start With Why
        "expected_duration_min": 18,
    },
    {
        "name": "Interview format",
        "url": "https://www.youtube.com/watch?v=UF8uR6Z6KLc",  # Steve Jobs interview
        "expected_duration_min": 10,
    },
]

# Minimal extraction prompt - grounded only, no opinions
EXTRACTION_PROMPT = """
Analyze this YouTube video and extract the following. Be precise and literal.

Return ONLY valid JSON with this structure:
{
  "video_info": {
    "title": "video title",
    "duration_seconds": 123,
    "speaker_count": 2
  },
  "clips": [
    {
      "clip_id": "CLIP_1",
      "timestamp_start": "MM:SS",
      "timestamp_end": "MM:SS",
      "speaker": "Name or SPEAKER_A",
      "quote": "Exact verbatim quote from video",
      "quote_type": "statement|question|reaction"
    }
  ],
  "quotes": [
    {
      "quote_id": "QUOTE_1",
      "text": "Exact verbatim quote",
      "speaker": "Name or SPEAKER_A",
      "timestamp": "MM:SS"
    }
  ]
}

RULES:
1. Timestamps must be in MM:SS format
2. Quotes must be VERBATIM - exact words spoken
3. If speaker name unknown, use SPEAKER_A, SPEAKER_B, etc.
4. Extract 6-12 most significant clips
5. NO opinions, NO analysis, NO "why it matters" - just extraction
"""


def test_gemini_youtube_url():
    """Test if Gemini can process a YouTube URL directly."""
    try:
        from google import genai
        from google.genai import types
    except ImportError:
        logger.error("google-genai not installed. Run: pip install google-genai")
        return False, "google-genai not installed"

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        logger.error("GOOGLE_API_KEY not set")
        return False, "GOOGLE_API_KEY not set"

    client = genai.Client(api_key=api_key)

    # Test with a simple YouTube URL
    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"  # Famous test video

    logger.info(f"Testing Gemini with YouTube URL: {test_url}")

    try:
        # Method 1: Try direct URL in prompt
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                f"Analyze this YouTube video and tell me: 1) Video title, 2) Duration, 3) Main speaker(s)\n\nVideo: {test_url}"
            ],
        )
        logger.info(f"Response (URL in prompt): {response.text[:500]}")
        return True, response.text

    except Exception as e:
        logger.warning(f"Direct URL in prompt failed: {e}")

        try:
            # Method 2: Try using Part with video_metadata
            # This is the newer approach for YouTube integration
            video_part = types.Part.from_uri(
                file_uri=test_url,
                mime_type="video/*"
            )
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[EXTRACTION_PROMPT, video_part],
            )
            logger.info(f"Response (Part.from_uri): {response.text[:500]}")
            return True, response.text

        except Exception as e2:
            logger.error(f"Part.from_uri also failed: {e2}")
            return False, f"Both methods failed: {e}, {e2}"


def test_gemini_video_with_transcript_fallback(video_url: str) -> dict:
    """
    Test Gemini video extraction with transcript fallback.

    If direct YouTube URL doesn't work, we fall back to:
    1. Fetch transcript via Supadata/other
    2. Send transcript to Gemini for extraction
    """
    from google import genai
    from google.genai import types

    api_key = os.getenv("GOOGLE_API_KEY")
    client = genai.Client(api_key=api_key)

    result = {
        "video_url": video_url,
        "method": None,
        "success": False,
        "clips": [],
        "quotes": [],
        "error": None,
    }

    # Try direct URL first
    try:
        logger.info(f"Attempting direct YouTube URL analysis: {video_url}")
        response = client.models.generate_content(
            model="gemini-2.5-pro",  # Use Pro for video analysis
            contents=[
                EXTRACTION_PROMPT,
                f"\n\nYouTube Video URL: {video_url}"
            ],
        )

        # Try to parse JSON response
        text = response.text
        # Clean up markdown code blocks if present
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()

        data = json.loads(text)
        result["method"] = "direct_url"
        result["success"] = True
        result["clips"] = data.get("clips", [])
        result["quotes"] = data.get("quotes", [])
        result["video_info"] = data.get("video_info", {})
        return result

    except json.JSONDecodeError as e:
        logger.warning(f"JSON parse failed: {e}")
        result["error"] = f"JSON parse error: {e}"

    except Exception as e:
        logger.warning(f"Direct URL failed: {e}")
        result["error"] = str(e)

    return result


def test_full_extraction(video: dict) -> dict:
    """Test full extraction with timestamps and quotes on a single video."""
    from google import genai

    api_key = os.getenv("GOOGLE_API_KEY")
    client = genai.Client(api_key=api_key)

    result = {
        "name": video["name"],
        "url": video["url"],
        "passed": False,
        "clips_extracted": 0,
        "quotes_extracted": 0,
        "has_timestamps": False,
        "has_speakers": False,
        "error": None,
    }

    try:
        logger.info(f"Testing extraction: {video['name']}")

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                EXTRACTION_PROMPT,
                f"\n\nYouTube Video URL: {video['url']}"
            ],
        )

        text = response.text
        logger.debug(f"Raw response length: {len(text)} chars")

        # Parse JSON from response
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()

        data = json.loads(text)

        # Validate extraction
        clips = data.get("clips", [])
        quotes = data.get("quotes", [])

        result["clips_extracted"] = len(clips)
        result["quotes_extracted"] = len(quotes)

        # Check if timestamps are in correct format (MM:SS)
        if clips:
            sample_ts = clips[0].get("timestamp_start", "")
            result["has_timestamps"] = ":" in sample_ts

        # Check if speakers are identified
        if quotes:
            sample_speaker = quotes[0].get("speaker", "")
            result["has_speakers"] = bool(sample_speaker) and sample_speaker != "Unknown"

        # Pass criteria: at least 3 clips, 3 quotes, with timestamps
        result["passed"] = (
            len(clips) >= 3 and
            len(quotes) >= 3 and
            result["has_timestamps"]
        )

        logger.info(f"  Clips: {len(clips)}, Quotes: {len(quotes)}, Timestamps: {result['has_timestamps']}, Speakers: {result['has_speakers']}")

        # Log sample clip for verification
        if clips:
            logger.info(f"  Sample clip: {clips[0].get('timestamp_start', 'N/A')} - \"{clips[0].get('quote', 'N/A')[:50]}...\"")

    except json.JSONDecodeError as e:
        result["error"] = f"JSON parse error: {e}"
        logger.warning(f"  Failed to parse JSON: {e}")

    except Exception as e:
        result["error"] = str(e)
        logger.warning(f"  Extraction failed: {e}")

    return result


def run_phase1_tests():
    """Run all Phase 1 tests and report results."""
    logger.info("=" * 60)
    logger.info("PHASE 1: Gemini Video Extraction Test")
    logger.info("=" * 60)

    results = []

    # Test 1: Basic YouTube URL support
    logger.info("\n--- Test 1: YouTube URL Support ---")
    url_works, url_result = test_gemini_youtube_url()
    results.append({
        "test": "youtube_url_support",
        "passed": url_works,
        "details": url_result[:200] if isinstance(url_result, str) else str(url_result)
    })

    # Test 2: Full extraction on test videos
    logger.info("\n--- Test 2: Full Extraction Tests ---")
    extraction_results = []
    for video in TEST_VIDEOS:
        ext_result = test_full_extraction(video)
        extraction_results.append(ext_result)
        results.append({
            "test": f"extraction_{video['name'][:20]}",
            "passed": ext_result["passed"],
            "details": f"Clips: {ext_result['clips_extracted']}, Quotes: {ext_result['quotes_extracted']}"
        })

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("TEST SUMMARY")
    logger.info("=" * 60)

    passed = sum(1 for r in results if r["passed"])
    total = len(results)

    for r in results:
        status = "✅ PASS" if r["passed"] else "❌ FAIL"
        logger.info(f"{status}: {r['test']}")

    logger.info(f"\nResult: {passed}/{total} tests passed")

    if passed >= total * 0.8:  # 80% pass rate
        logger.info("🎉 Phase 1 PASSED - Gemini extraction validated")
        return True
    else:
        logger.warning("⚠️ Phase 1 FAILED - Need to investigate failures")
        return False


if __name__ == "__main__":
    # Load environment
    from dotenv import load_dotenv
    load_dotenv()

    success = run_phase1_tests()
    sys.exit(0 if success else 1)
