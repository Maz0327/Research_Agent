"""Packer round 2: the seed video + sources answering the machine's own 5 gap asks."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import backend.config  # noqa: F401
from backend.state import create_job
from backend.worker import run_research_job

TOPIC = (
    "The full story behind a prospector's horrifying 1874 ordeal in Colorado's "
    "San Juan Mountains — what really happened, beyond what this video tells"
)
ARTICLES = [
    "https://coloradoencyclopedia.org/article/alferd-packer",
    "https://en.wikipedia.org/wiki/Alferd_Packer",
    "https://www.lawweekcolorado.com/article/the-colorado-cannibal-the-story-of-alferd-packer/",
    "https://history.denverlibrary.org/news/western-history/alferd-packer-truth-out-there-or-right-here",
    "https://www.colorado.gov/pacific/archives/alfred-packer",
    "https://www.upi.com/Archives/1989/10/13/Alfred-Packer-ate-em-forensic-expert-says/1786624254400/",
    "https://www.nationalgeographic.com/magazine/article/colorado-cannibal-companions-wilderness-survival-archaeology",
    "https://en.wikipedia.org/wiki/Polly_Pry",
    "https://www.townoflakecityco.gov/alferd-packer",
    "https://www.truewestmagazine.com/article/cannibal-correspondence/",
]
config_json = {
    "topic": TOPIC, "job_type": "mixed_input", "input_mode": "mixed",
    "video_urls": ["https://www.youtube.com/watch?v=TlAXZVdAhIo"],
    "article_urls": ARTICLES, "text_inputs": [], "screenshots": [],
    "source_count": 1 + len(ARTICLES), "duplicates_removed": 0,
}
job = create_job(config_json=config_json)
print(f"JOB_ID={job.job_id}")
result = run_research_job(job.job_id, TOPIC)
print("RESULT:", {k: v for k, v in result.items() if k not in ("documents",)})
