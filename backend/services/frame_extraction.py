"""Frame extraction service for visual analysis.

Extracts keyframes from video files using ffmpeg for analysis
by vision models (Kimi K2.5).

Requirements:
    - ffmpeg must be installed and available on PATH
    - Sufficient disk space for extracted frames

Usage:
    from backend.services.frame_extraction import extract_keyframes

    result = extract_keyframes("path/to/video.mp4")
    print(result.frames)  # List of Path objects
    result.cleanup()       # Remove temp files when done
"""

import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from loguru import logger


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DEFAULT_INTERVAL_SECONDS = 5     # Extract one frame every 5 seconds
DEFAULT_MAX_FRAMES = 20          # Vision API limit
FFMPEG_TIMEOUT_SECONDS = 120     # 2 minute timeout for extraction
FRAME_SCALE = "1920:-1"          # Scale to 1920px wide, keep aspect ratio
FRAME_QUALITY = "2"              # JPEG quality (2 = high, 31 = low)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------
class FrameExtractionError(Exception):
    """Raised when frame extraction fails."""
    def __init__(self, message: str, video_path: str = ""):
        self.message = message
        self.video_path = video_path
        super().__init__(message)


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------
@dataclass
class FrameExtractionResult:
    """Result of frame extraction."""
    frames: list[Path] = field(default_factory=list)
    source_id: str = ""
    frame_count: int = 0
    output_dir: Optional[Path] = None

    def cleanup(self) -> None:
        """Remove extracted frames and temp directory."""
        if not self.output_dir or not self.output_dir.exists():
            return
        try:
            for frame in self.frames:
                if frame.exists():
                    frame.unlink()
            # Only remove dir if empty
            if self.output_dir.exists() and not any(self.output_dir.iterdir()):
                self.output_dir.rmdir()
            logger.debug(f"Cleaned up {self.frame_count} frames from {self.output_dir}")
        except Exception as e:
            logger.warning(f"Failed to cleanup frames: {e}")


# ---------------------------------------------------------------------------
# Core extraction function
# ---------------------------------------------------------------------------
def extract_keyframes(
    video_path: str,
    source_id: str = "",
    output_dir: Optional[str] = None,
    interval_seconds: int = DEFAULT_INTERVAL_SECONDS,
    max_frames: int = DEFAULT_MAX_FRAMES,
) -> FrameExtractionResult:
    """Extract keyframes from video at specified interval.

    Uses ffmpeg to extract frames at regular intervals. Frames are saved
    as JPEG files in the output directory.

    Args:
        video_path: Path to video file (local path or downloaded temp file)
        source_id: Source identifier for tracking
        output_dir: Directory to save frames (temp dir if None)
        interval_seconds: Seconds between frames (default: 5)
        max_frames: Maximum number of frames to extract (default: 20)

    Returns:
        FrameExtractionResult with frame paths and metadata

    Raises:
        FrameExtractionError: If ffmpeg is not installed, video not found,
            or extraction fails
    """
    video = Path(video_path)
    if not video.exists():
        raise FrameExtractionError(
            f"Video file not found: {video_path}",
            video_path=video_path,
        )

    # Check ffmpeg is available
    try:
        subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            check=True,
            timeout=10,
        )
    except FileNotFoundError:
        raise FrameExtractionError(
            "ffmpeg not found. Install with: brew install ffmpeg (macOS) "
            "or apt install ffmpeg (Linux)",
            video_path=video_path,
        )
    except subprocess.TimeoutExpired:
        raise FrameExtractionError(
            "ffmpeg version check timed out",
            video_path=video_path,
        )

    # Create output directory
    if output_dir:
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)
    else:
        out_path = Path(tempfile.mkdtemp(prefix="ra_frames_"))

    logger.info(
        f"Extracting frames from {video.name} "
        f"(interval={interval_seconds}s, max={max_frames})"
    )

    # Build ffmpeg command
    # -vf fps=1/N: extract 1 frame every N seconds
    # -vframes max: limit total frames
    # -q:v 2: high quality JPEG
    cmd = [
        "ffmpeg",
        "-i", str(video),
        "-vf", f"fps=1/{interval_seconds},scale={FRAME_SCALE}",
        "-vframes", str(max_frames),
        "-q:v", FRAME_QUALITY,
        "-y",  # Overwrite existing
        str(out_path / "frame_%04d.jpg"),
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            check=True,
            timeout=FFMPEG_TIMEOUT_SECONDS,
        )
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode("utf-8", errors="replace")[:500]
        raise FrameExtractionError(
            f"ffmpeg extraction failed: {stderr}",
            video_path=video_path,
        )
    except subprocess.TimeoutExpired:
        raise FrameExtractionError(
            f"Frame extraction timed out after {FFMPEG_TIMEOUT_SECONDS}s",
            video_path=video_path,
        )

    # Collect extracted frames
    frames = sorted(out_path.glob("frame_*.jpg"))
    frame_count = len(frames)

    if frame_count == 0:
        logger.warning(f"No frames extracted from {video.name}")
    else:
        logger.info(f"Extracted {frame_count} frames from {video.name}")

    return FrameExtractionResult(
        frames=frames,
        source_id=source_id,
        frame_count=frame_count,
        output_dir=out_path,
    )
