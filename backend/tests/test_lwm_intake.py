"""Intake: every input kind, dedup, persistence — the 1B/1C contract."""

import json
import shutil
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures" / "lwm"


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    ws = tmp_path / "ws"
    shutil.copytree(FIXTURES / "workspace", ws)
    monkeypatch.setenv("LWM_WORKSPACE", str(ws))
    return ws


@pytest.fixture
def episode(workspace):
    from backend.lwm import episode as ep
    return Path(ep.create("The Vela Incident", offline=True)["path"])


class TestClassification:
    def test_youtube_is_first_class_not_just_a_url(self):
        from backend.lwm.manifest import classify
        kind, canonical = classify("https://youtu.be/TlAXZVdAhIo?t=99")
        assert kind == "youtube"
        assert canonical == "https://www.youtube.com/watch?v=TlAXZVdAhIo"

    def test_web_url(self):
        from backend.lwm.manifest import classify
        assert classify("https://example.com/story?utm_source=x")[0] == "url"

    def test_existing_file_and_image(self, tmp_path):
        from backend.lwm.manifest import classify
        pdf = tmp_path / "case.pdf"
        pdf.write_bytes(b"%PDF-1.4 x")
        img = tmp_path / "shot.png"
        img.write_bytes(b"\x89PNG x")
        assert classify(str(pdf))[0] == "file"
        assert classify(str(img))[0] == "image"

    def test_anything_else_is_a_preserved_note(self):
        from backend.lwm.manifest import classify
        assert classify("why did his story change so many times?")[0] == "note"


class TestAddSource:
    def test_note_text_is_preserved_verbatim(self, episode):
        from backend.lwm.manifest import add_source
        text = "I think the interesting question is why his story changed.\nLine two."
        entry = add_source(episode, text, offline=True)
        assert (episode / entry["preserved_path"]).read_text() == text

    def test_file_is_copied_into_the_inbox(self, episode, tmp_path):
        from backend.lwm.manifest import add_source
        f = tmp_path / "notes.md"
        f.write_text("# research notes")
        entry = add_source(episode, str(f), offline=True)
        assert (episode / entry["preserved_path"]).read_text() == "# research notes"
        assert entry["ingestion_status"] == "pending"

    def test_docx_is_preserved_and_marked_not_silently_ignored(self, episode, tmp_path):
        from backend.lwm.manifest import add_source
        f = tmp_path / "old.docx"
        f.write_bytes(b"PK docx")
        entry = add_source(episode, str(f), offline=True)
        assert entry["ingestion_status"] == "preserved"
        assert "unsupported" in entry["processing"]

    def test_image_is_a_valid_source_with_status(self, episode, tmp_path):
        from backend.lwm.manifest import add_source
        f = tmp_path / "grave.png"
        f.write_bytes(b"\x89PNG")
        entry = add_source(episode, str(f), offline=True)
        assert entry["type"] == "image"
        assert "OCR" in entry["processing"]

    def test_duplicate_url_returns_existing_entry(self, episode):
        from backend.lwm.manifest import add_source
        a = add_source(episode, "https://youtu.be/TlAXZVdAhIo", offline=True)
        b = add_source(episode, "https://www.youtube.com/watch?v=TlAXZVdAhIo&t=5", offline=True)
        assert b["duplicate"] is True and b["id"] == a["id"]

    def test_duplicate_file_by_content_hash(self, episode, tmp_path):
        from backend.lwm.manifest import add_source
        f1 = tmp_path / "a.txt"
        f1.write_text("same bytes")
        f2 = tmp_path / "b.txt"
        f2.write_text("same bytes")
        a = add_source(episode, str(f1), offline=True)
        b = add_source(episode, str(f2), offline=True)
        assert b["duplicate"] is True and b["id"] == a["id"]

    def test_unsupported_extension_surfaces_clearly(self, episode, tmp_path):
        from backend.lwm.manifest import add_source
        f = tmp_path / "raw.xyz"
        f.write_bytes(b"???")
        entry = add_source(episode, str(f), offline=True)
        assert entry["ingestion_status"] == "unsupported"
        assert entry["errors"]

    def test_manifest_is_persistent_and_machine_readable(self, episode):
        from backend.lwm.manifest import add_source, load
        add_source(episode, "https://example.com/a", offline=True)
        data = json.loads((episode / "SOURCE-MANIFEST.json").read_text())
        assert data["sources"][0]["id"] == "S01"
        assert load(episode)["sources"][0]["ingestion_status"]


class TestMixedIntakeAndRouting:
    def test_mixed_input_in_one_episode_routes_correctly(self, episode, tmp_path):
        from backend.lwm.manifest import add_source, pending_for_research
        pdf = tmp_path / "trial.pdf"
        pdf.write_bytes(b"%PDF")
        add_source(episode, "https://youtu.be/TlAXZVdAhIo", offline=True)
        add_source(episode, "https://youtu.be/dQw4w9WgXcQ", offline=True)
        add_source(episode, "https://example.com/parole-campaign", offline=True)
        add_source(episode, str(pdf), offline=True)
        add_source(episode, "note: check the 1907 vs 1909 death year", offline=True)
        pending = pending_for_research(episode)
        assert len(pending["video_urls"]) == 2
        assert any("parole" in u for u in pending["article_urls"])
        assert any("1907" in t for t in pending["text_inputs"])
