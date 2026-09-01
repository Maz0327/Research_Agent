"""Where the workspace lives, and the files inside an episode.

Everything resolves through LWM_WORKSPACE so tests run against a temporary
workspace and can never touch the real one by accident.
"""

import os
from pathlib import Path


def workspace() -> Path:
    return Path(os.environ.get("LWM_WORKSPACE", os.path.expanduser("~/.openclaw/workspace")))

def pipeline_dir() -> Path:
    return workspace() / "pipeline"

def episodes_dir() -> Path:
    return pipeline_dir() / "episodes"

def active_episode_file() -> Path:
    return pipeline_dir() / "ACTIVE-EPISODE.txt"

def template_dir() -> Path:
    return episodes_dir() / "_TEMPLATE"

def episode_dir(slug: str) -> Path:
    return episodes_dir() / slug

def read_active_episode() -> str | None:
    """The one pointer. Comment lines are ignored; the slug line wins."""
    f = active_episode_file()
    if not f.exists():
        return None
    for line in f.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            return line
    return None

def set_active_episode(slug: str) -> None:
    f = active_episode_file()
    header = ""
    if f.exists():
        header = "".join(
            line for line in f.read_text().splitlines(keepends=True) if line.startswith("#")
        )
    f.write_text(header + "\n" + slug + "\n" if header else slug + "\n")
