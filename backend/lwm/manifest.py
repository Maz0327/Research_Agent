"""The episode source manifest — what Maz gave the system, and what happened to it.

One JSON file per episode: `SOURCE-MANIFEST.json`. This is the INTAKE record,
deliberately distinct from Research Agent Doc 0: the manifest answers "what
did Maz give us and what happened to each input"; Doc 0 answers "what did the
research process actually ingest and what does the record contain". Neither
replaces the other.
"""

import hashlib
import json
import re
import shutil
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import parse_qs, urlparse

TYPES = ("youtube", "url", "file", "image", "note")
STATUSES = ("preserved", "pending", "ingested", "unsupported", "error")

_YT_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be", "music.youtube.com"}
_IMAGE_EXT = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".heic"}
_FILE_EXT = {".pdf", ".txt", ".md", ".markdown", ".docx", ".srt", ".vtt", ".json", ".csv"}
# What the Research Agent can actually ingest today (worker mixed-input modes).
_RA_INGESTIBLE_EXT = {".pdf", ".txt", ".md", ".markdown", ".srt", ".vtt"}


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def youtube_id(url: str) -> str | None:
    """The stable video id, or None when the URL is not YouTube."""
    p = urlparse(url)
    if p.hostname not in _YT_HOSTS:
        return None
    if p.hostname == "youtu.be":
        vid = p.path.lstrip("/").split("/")[0]
        return vid or None
    if p.path.startswith("/watch"):
        return (parse_qs(p.query).get("v") or [None])[0]
    m = re.match(r"^/(shorts|live|embed)/([A-Za-z0-9_-]{6,})", p.path)
    return m.group(2) if m else None


def canonical_url(url: str) -> str:
    """One canonical form per real source, so duplicates collide.

    YouTube collapses to watch?v=<id>. Everything else drops fragments and
    tracking params but keeps meaningful query strings.
    """
    vid = youtube_id(url)
    if vid:
        return f"https://www.youtube.com/watch?v={vid}"
    p = urlparse(url)
    query = "&".join(
        f"{k}={v[0]}" for k, v in sorted(parse_qs(p.query).items())
        if not k.startswith(("utm_", "fbclid", "gclid", "ref"))
    )
    return f"{p.scheme or 'https'}://{(p.hostname or '').lower()}{p.path.rstrip('/')}" + (f"?{query}" if query else "")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def classify(raw: str) -> tuple[str, str]:
    """(type, canonical) for one input. Files are recognized by existing paths."""
    candidate = Path(raw).expanduser()
    if candidate.exists() and candidate.is_file():
        ext = candidate.suffix.lower()
        return ("image" if ext in _IMAGE_EXT else "file"), str(candidate.resolve())
    if re.match(r"^https?://", raw.strip()):
        url = raw.strip()
        return ("youtube" if youtube_id(url) else "url"), canonical_url(url)
    return "note", raw


def manifest_path(episode: Path) -> Path:
    return episode / "SOURCE-MANIFEST.json"


def load(episode: Path) -> dict:
    p = manifest_path(episode)
    if p.exists():
        return json.loads(p.read_text())
    return {"episode": episode.name, "created_at": _now(), "sources": []}


def save(episode: Path, data: dict) -> None:
    manifest_path(episode).write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n")


def _youtube_metadata(url: str) -> dict:
    """Best-effort title/channel via oEmbed. Offline-safe: failures are recorded, not raised."""
    try:
        import urllib.request
        req = urllib.request.Request(
            f"https://www.youtube.com/oembed?url={url}&format=json",
            headers={"User-Agent": "lwm-intake/1"})
        with urllib.request.urlopen(req, timeout=6) as r:
            meta = json.loads(r.read())
        return {"title": meta.get("title"), "channel": meta.get("author_name")}
    except Exception as e:
        return {"metadata_error": f"oEmbed unavailable: {e.__class__.__name__}"}


def add_source(episode: Path, raw: str, role: str = "user", offline: bool = False) -> dict:
    """Register one input. Duplicates return the existing entry, marked.

    Returns the manifest entry, with `duplicate: True` when the input was
    already registered — the original is never deleted or replaced.
    """
    data = load(episode)
    kind, canonical = classify(raw)

    # Dedup key: canonical URL for links, content hash for files, exact text for notes.
    if kind in ("file", "image"):
        key = _sha256(Path(canonical))
    elif kind == "note":
        key = hashlib.sha256(canonical.encode()).hexdigest()
    else:
        key = canonical
    for entry in data["sources"]:
        if entry.get("dedup_key") == key:
            return {**entry, "duplicate": True}

    sid = f"S{len(data['sources']) + 1:02d}"
    entry = {
        "id": sid,
        "type": kind,
        "original_input": raw if kind != "note" else None,
        "canonical": canonical if kind != "note" else None,
        "title": None,
        "role": role,
        "added_at": _now(),
        "ingestion_status": "pending",
        "ra_source_id": None,
        "errors": [],
        "dedup_key": key,
    }

    inbox = episode / "inbox"
    inbox.mkdir(exist_ok=True)

    if kind == "youtube":
        entry["video_id"] = youtube_id(raw)
        entry["transcript_status"] = "pending (Supadata/captions at research time)"
        entry["watch_status"] = "available (watch skill / vision seat) — not auto-run"
        if not offline:
            entry.update(_youtube_metadata(canonical))
    elif kind == "note":
        # Preserve the exact text; the manifest carries a pointer, never a paraphrase.
        note_file = inbox / f"{sid}-note.md"
        note_file.write_text(canonical)
        entry["preserved_path"] = str(note_file.relative_to(episode))
        entry["title"] = (canonical.strip().splitlines() or ["note"])[0][:80]
        entry["ingestion_status"] = "preserved"
    elif kind in ("file", "image"):
        src = Path(canonical)
        dest = inbox / f"{sid}-{src.name}"
        shutil.copy2(src, dest)
        entry["preserved_path"] = str(dest.relative_to(episode))
        entry["title"] = src.name
        ext = src.suffix.lower()
        if kind == "image":
            entry["ingestion_status"] = "preserved"
            entry["processing"] = "RA screenshot/OCR path available at research time"
        elif ext == ".docx":
            entry["ingestion_status"] = "preserved"
            entry["processing"] = "unsupported for automated ingestion today — convert to PDF/TXT or it stays reference-only"
        elif ext in _RA_INGESTIBLE_EXT:
            entry["ingestion_status"] = "pending"
        else:
            entry["ingestion_status"] = "unsupported"
            entry["errors"].append(f"no automated ingestion for {ext}")
    else:  # plain URL
        entry["title"] = canonical

    data["sources"].append(entry)
    save(episode, data)
    return entry


def pending_for_research(episode: Path) -> dict:
    """What the next research round would receive, grouped the way RA wants it."""
    data = load(episode)
    out = {"video_urls": [], "article_urls": [], "text_inputs": [], "screenshots": [], "unsupported": []}
    for s in data["sources"]:
        if s.get("ingestion_status") == "ingested":
            continue
        if s["type"] == "youtube":
            out["video_urls"].append(s["canonical"])
        elif s["type"] == "url":
            out["article_urls"].append(s["canonical"])
        elif s["type"] == "note":
            out["text_inputs"].append((episode / s["preserved_path"]).read_text())
        elif s["type"] == "image":
            out["screenshots"].append(str(episode / s["preserved_path"]))
        elif s["type"] == "file":
            p = episode / s["preserved_path"]
            if p.suffix.lower() in _RA_INGESTIBLE_EXT and p.suffix.lower() != ".pdf":
                out["text_inputs"].append(p.read_text(errors="replace"))
            elif p.suffix.lower() == ".pdf":
                out["article_urls"].append(str(p))  # RA ingests PDFs by path/url route
            else:
                out["unsupported"].append(s["id"])
    return out


def mark_ingested(episode: Path, ra_source_map: dict[str, str]) -> None:
    """After a research round: record RA source ids against manifest entries."""
    data = load(episode)
    for s in data["sources"]:
        key = s.get("canonical") or s.get("preserved_path") or ""
        for match, ra_id in ra_source_map.items():
            if match and match in key:
                s["ra_source_id"] = ra_id
                s["ingestion_status"] = "ingested"
    save(episode, data)
