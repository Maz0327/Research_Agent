"""OpenAI Whisper API client for YouTube audio transcription."""
import os
import re
import tempfile
from pathlib import Path
from typing import Dict, Optional
import subprocess
from loguru import logger
import openai

from backend.utils.error_handling import sanitize_error_message
from backend.utils.rate_limiter import with_rate_limit


class WhisperTranscriptionClient:
    """
    OpenAI Whisper API for transcribing YouTube videos without captions.

    This is TIER 2 of the transcript system.
    - Cost: $0.006/minute
    - Only use when youtube-transcript-api fails (Tier 1)
    - Downloads audio with yt-dlp, then transcribes

    DO NOT skip Tier 1. Always try native captions first!
    """

    # OpenAI Whisper API file size limit (25MB)
    MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024

    def __init__(self):
        """Initialize Whisper client using Settings for API key."""
        from backend.config import get_settings
        settings = get_settings()
        self.api_key = settings.openai_api_key
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY required for Whisper transcription")
        self.client = openai.OpenAI(api_key=self.api_key)
        self.cost_per_minute = 0.006

    @staticmethod
    def _validate_video_id(video_id: str) -> str:
        """
        Validate YouTube video ID format to prevent command injection.

        YouTube video IDs are 11 characters: alphanumeric, dash, and underscore.

        Args:
            video_id: YouTube video ID to validate

        Returns:
            Validated video ID

        Raises:
            ValueError: If video_id format is invalid
        """
        if not re.match(r'^[A-Za-z0-9_-]{11}$', video_id):
            raise ValueError(f"Invalid YouTube video ID format: {video_id}")
        return video_id

    def download_audio(self, video_id: str, output_dir: Optional[str] = None) -> str:
        """
        Download audio from YouTube video using yt-dlp.

        Args:
            video_id: YouTube video ID
            output_dir: Directory to save audio (uses temp if not specified)

        Returns:
            Path to downloaded audio file

        Raises:
            ValueError: If video_id format is invalid
        """
        # Validate video ID format to prevent command injection
        video_id = self._validate_video_id(video_id)

        if output_dir is None:
            output_dir = tempfile.mkdtemp()

        output_path = Path(output_dir) / f"{video_id}.mp3"

        try:
            logger.info(f"Downloading audio for {video_id}...")

            # Use yt-dlp to download audio only
            cmd = [
                "yt-dlp",
                "-x",  # Extract audio
                "--audio-format", "mp3",
                "--audio-quality", "128K",
                "-o", str(output_path),
                f"https://www.youtube.com/watch?v={video_id}",
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 min timeout
            )

            if result.returncode != 0:
                logger.error(f"yt-dlp failed: {result.stderr}")
                raise RuntimeError(f"yt-dlp failed: {result.stderr}")

            logger.info(f"Audio downloaded: {output_path}")
            return str(output_path)

        except subprocess.TimeoutExpired:
            raise RuntimeError("Audio download timed out")
        except Exception as e:
            sanitized = sanitize_error_message(e, include_type=False)
            raise RuntimeError(f"Failed to download audio: {sanitized}")

    @staticmethod
    def _segment_field(segment, name: str, default):
        """Read one field from a Whisper segment.

        The OpenAI SDK returns `TranscriptionSegment` objects (attribute
        access) for `verbose_json`, but cached/replayed payloads and tests
        hand back plain dicts. Support both.

        Args:
            segment: A `TranscriptionSegment` object or a dict.
            name: Field name to read.
            default: Value to return when the field is missing or None.

        Returns:
            The field value, or `default` when absent.
        """
        value = (
            segment.get(name, default)
            if isinstance(segment, dict)
            else getattr(segment, name, default)
        )
        return default if value is None else value

    @classmethod
    def _normalize_segments(cls, raw_segments) -> list:
        """Normalize Whisper segments to plain start/end/text dicts.

        Args:
            raw_segments: Whatever the SDK put on `response.segments`: a list
                of `TranscriptionSegment` objects, a list of dicts, or None.

        Returns:
            List of dicts with `start`, `end`, and `text` keys. Empty when the
            response carried no segments.
        """
        if not raw_segments:
            return []
        return [
            {
                "start": cls._segment_field(seg, "start", 0),
                "end": cls._segment_field(seg, "end", 0),
                "text": cls._segment_field(seg, "text", ""),
            }
            for seg in raw_segments
        ]

    @with_rate_limit("whisper")
    def transcribe(
        self,
        audio_path: str,
        language: str = "en",
    ) -> Dict:
        """
        Transcribe audio file using Whisper API.

        Args:
            audio_path: Path to audio file
            language: Language code (en, es, fr, etc.)

        Returns:
            Dict with transcript and metadata
        """
        try:
            logger.info(f"Transcribing with Whisper: {audio_path}")

            # Get audio duration for cost estimation
            duration_minutes = self._get_audio_duration(audio_path)

            with open(audio_path, "rb") as audio_file:
                response = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language=language,
                    response_format="verbose_json",  # Includes timestamps
                )

            # Extract segments with timestamps
            segments = self._normalize_segments(getattr(response, "segments", None))

            cost = duration_minutes * self.cost_per_minute

            logger.info(f"Whisper transcription complete: {len(segments)} segments, ${cost:.4f}")

            return {
                "text": response.text,
                "segments": segments,
                "language": language,
                "duration_minutes": duration_minutes,
                "method": "whisper",
                "cost": cost,
            }

        except Exception as e:
            sanitized = sanitize_error_message(e, include_type=False)
            logger.error(f"Whisper transcription failed: {sanitized}")
            raise RuntimeError(f"Whisper transcription failed: {sanitized}") from e

    def _get_audio_duration(self, audio_path: str) -> float:
        """Get audio duration in minutes."""
        try:
            # Try using ffprobe (part of ffmpeg)
            cmd = [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                audio_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                duration_seconds = float(result.stdout.strip())
                return duration_seconds / 60.0
        except (subprocess.SubprocessError, ValueError, OSError):
            pass

        # Fallback: estimate from file size (~128kbps)
        file_size = os.path.getsize(audio_path)
        return (file_size / 16000) / 60.0  # Rough estimate

    def _compress_audio(self, audio_path: str, target_bitrate: str = "48k") -> str:
        """
        Compress audio file to reduce size below Whisper API limit.

        Uses ffmpeg to re-encode audio at lower bitrate (mono, 48kbps).
        Speech is still intelligible at this bitrate.

        Args:
            audio_path: Path to audio file
            target_bitrate: Target bitrate (default 48k for speech)

        Returns:
            Path to compressed audio file

        Raises:
            RuntimeError: If compression fails
        """
        output_path = audio_path.replace(".mp3", "_compressed.mp3")

        try:
            logger.info(f"Compressing audio from {os.path.getsize(audio_path) / 1024 / 1024:.1f}MB...")

            cmd = [
                "ffmpeg",
                "-y",  # Overwrite output
                "-i", audio_path,
                "-ac", "1",  # Mono
                "-ab", target_bitrate,  # Target bitrate
                "-ar", "16000",  # 16kHz sample rate (optimal for speech)
                output_path,
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 min timeout
            )

            if result.returncode != 0:
                logger.error(f"ffmpeg compression failed: {result.stderr}")
                raise RuntimeError(f"Audio compression failed: {result.stderr}")

            new_size = os.path.getsize(output_path)
            logger.info(f"Audio compressed to {new_size / 1024 / 1024:.1f}MB")

            return output_path

        except subprocess.TimeoutExpired:
            raise RuntimeError("Audio compression timed out")
        except Exception as e:
            sanitized = sanitize_error_message(e, include_type=False)
            raise RuntimeError(f"Failed to compress audio: {sanitized}")

    def transcribe_youtube(
        self,
        video_id: str,
        max_duration_minutes: float = 60.0,
    ) -> Dict:
        """
        Full pipeline: download audio and transcribe.

        This is the main function. Use it for Tier 2 transcription.

        Args:
            video_id: YouTube video ID
            max_duration_minutes: Maximum video length to transcribe

        Returns:
            Dict with transcript and cost
        """
        audio_path = None
        compressed_path = None

        try:
            # Download audio
            audio_path = self.download_audio(video_id)

            # Check duration
            duration = self._get_audio_duration(audio_path)
            if duration > max_duration_minutes:
                raise ValueError(f"Video too long: {duration:.1f}m > {max_duration_minutes}m limit")

            # Check file size - Whisper API has 25MB limit
            file_size = os.path.getsize(audio_path)
            transcribe_path = audio_path

            if file_size > self.MAX_FILE_SIZE_BYTES:
                logger.warning(
                    f"Audio file {file_size / 1024 / 1024:.1f}MB exceeds "
                    f"Whisper limit of {self.MAX_FILE_SIZE_BYTES / 1024 / 1024:.0f}MB, compressing..."
                )
                compressed_path = self._compress_audio(audio_path)
                transcribe_path = compressed_path

                # Verify compressed size
                compressed_size = os.path.getsize(compressed_path)
                if compressed_size > self.MAX_FILE_SIZE_BYTES:
                    raise ValueError(
                        f"Audio still too large after compression: "
                        f"{compressed_size / 1024 / 1024:.1f}MB > 25MB limit"
                    )

            # Transcribe
            result = self.transcribe(transcribe_path)
            result["video_id"] = video_id

            return result

        except Exception as e:
            sanitized = sanitize_error_message(e, include_type=False)
            logger.error(f"YouTube transcription failed for {video_id}: {sanitized}")
            raise RuntimeError(f"YouTube transcription failed: {sanitized}") from e

        finally:
            # Cleanup all audio files
            for path in [audio_path, compressed_path]:
                if path:
                    try:
                        os.remove(path)
                    except OSError:
                        pass


def transcribe_with_whisper(video_id: str, max_duration: float = 60.0) -> Dict:
    """
    Transcribe YouTube video with Whisper API.

    Use this as Tier 2 fallback when youtube-transcript-api fails.
    """
    client = WhisperTranscriptionClient()
    return client.transcribe_youtube(video_id, max_duration)
