"""Clean-run test: mixed-input job from a single seed video, vague topic.

The owner-picked seed: youtu.be/TlAXZVdAhIo (Scary Interesting, Alfred Packer).
Topic is deliberately vague — the test is how much the pipeline recovers and
what its gap analysis asks for next.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import backend.config  # noqa: F401  (dotenv load)
from backend.state import create_job
from backend.worker import run_research_job

TOPIC = (
    "The full story behind a prospector's horrifying 1874 ordeal in Colorado's "
    "San Juan Mountains — what really happened, beyond what this video tells"
)
config_json = {
    "topic": TOPIC,
    "job_type": "mixed_input",
    "input_mode": "mixed",
    "video_urls": ["https://www.youtube.com/watch?v=TlAXZVdAhIo"],
    "article_urls": [],
    "text_inputs": [],
    "screenshots": [],
    "source_count": 1,
    "duplicates_removed": 0,
}
job = create_job(config_json=config_json)
print(f"JOB_ID={job.job_id}")
result = run_research_job(job.job_id, TOPIC)
print("RESULT:", {k: v for k, v in result.items() if k != "documents"})
