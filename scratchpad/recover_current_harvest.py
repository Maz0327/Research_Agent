"""Recover only the accepted D-038 run's harvest from its checked-in sources.

The original 1,253-fact scratchpad file was not tracked. This script replays
the settled harvest stage against the exact 16-source, 42,263-word Source Vault
and checkpoints after every source. It does not run any other pipeline stage.
The model output is nondeterministic, so a replay is not forced to the old count.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.config import get_settings  # noqa: E402
from backend.integrations.structured_client import get_structured_client  # noqa: E402
from backend.pipeline.stages.harvest_stage import harvest_source  # noqa: E402
from scratchpad.build_semantic_labeling_current_read import (  # noqa: E402
    DEFAULT_HARVEST,
    DEFAULT_SOURCE_VAULT,
    read_source_vault,
    stable_hash,
)


def source_signature(sources: list[dict[str, Any]]) -> list[list[str]]:
    return [
        [source["source_id"], source["title"], source["url"], source["full_text"]]
        for source in sources
    ]


def harvest_configuration(settings: Any) -> dict[str, Any]:
    return {
        "harvest_max_chars": settings.harvest_max_chars,
        "harvest_chunk_overlap": settings.harvest_chunk_overlap,
        "harvest_facts_per_1000": settings.harvest_facts_per_1000,
    }


def checkpoint_payload(
    harvest: dict[str, list[str]], sources: list[dict[str, Any]], settings: Any
) -> dict[str, Any]:
    return {
        "metadata": {
            "schema_version": 1,
            "source_vault_sha256": stable_hash(source_signature(sources)),
            "source_text_sha256_by_id": {
                source["source_id"]: stable_hash(source["full_text"])
                for source in sources
            },
            "source_count": len(sources),
            "source_word_count": sum(
                len(source["full_text"].split()) for source in sources
            ),
            "harvest_model": settings.model_harvest,
            "harvest_configuration": harvest_configuration(settings),
            "completed_source_ids": list(harvest),
            "harvest_fact_count": sum(map(len, harvest.values())),
            "harvest_sha256": stable_hash(harvest),
            "checkpointed_at": datetime.now(UTC).isoformat(),
        },
        "harvest": harvest,
    }


def write_checkpoint(
    path: Path,
    harvest: dict[str, list[str]],
    sources: list[dict[str, Any]],
    settings: Any,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".partial")
    temporary.write_text(
        json.dumps(
            checkpoint_payload(harvest, sources, settings),
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-vault", type=Path, default=DEFAULT_SOURCE_VAULT)
    parser.add_argument("--output", type=Path, default=DEFAULT_HARVEST)
    parser.add_argument(
        "--adopt-existing",
        action="store_true",
        help="Record provenance for a verified legacy plain-dict checkpoint.",
    )
    args = parser.parse_args()

    sources = read_source_vault(args.source_vault)
    word_count = sum(len(source["full_text"].split()) for source in sources)
    if len(sources) != 16 or word_count != 42263:
        raise ValueError(
            f"Expected the accepted 16-source/42,263-word vault; got "
            f"{len(sources)} sources and {word_count:,} words"
        )

    settings = get_settings()
    harvest: dict[str, list[str]] = {}
    if args.output.exists():
        payload = json.loads(args.output.read_text(encoding="utf-8"))
        if "metadata" in payload and "harvest" in payload:
            harvest = payload["harvest"]
            expected = checkpoint_payload(harvest, sources, settings)["metadata"]
            held = payload["metadata"]
            for key in (
                "source_vault_sha256",
                "source_text_sha256_by_id",
                "harvest_model",
                "harvest_configuration",
                "harvest_fact_count",
                "harvest_sha256",
            ):
                if held.get(key) != expected[key]:
                    raise ValueError(f"Existing harvest provenance mismatch: {key}")
        elif args.adopt_existing:
            harvest = payload
        else:
            raise ValueError(
                "Existing harvest has no provenance; inspect it, then rerun with "
                "--adopt-existing only if it is the verified current replay"
            )
    missing = [source for source in sources if source["source_id"] not in harvest]
    if not missing:
        write_checkpoint(args.output, harvest, sources, settings)
        print(f"Harvest already complete: {sum(map(len, harvest.values()))} facts")
        return

    # A stale GOOGLE_API_KEY can make the OpenAI SDK select the wrong auth path.
    os.environ.pop("GOOGLE_API_KEY", None)
    client = get_structured_client(settings.model_harvest)
    total_cost = 0.0
    for source in missing:
        source_id = source["source_id"]
        source_type = "youtube" if "youtu" in source["url"] else "article"
        mode = "transcript_grounded" if source_type == "youtube" else "article_fetched"
        started = time.monotonic()
        facts, cost = harvest_source(
            client=client,
            source_id=source_id,
            title=source["title"],
            text=source["full_text"],
            mode=mode,
            ceiling="HIGH",
        )
        harvest[source_id] = facts
        total_cost += cost
        write_checkpoint(args.output, harvest, sources, settings)
        print(
            f"{len(harvest):02d}/16 {source_id} "
            f"{len(source['full_text'].split()):,}w -> {len(facts)} facts "
            f"({time.monotonic() - started:.1f}s)",
            flush=True,
        )

    print(
        f"HARVEST: {sum(map(len, harvest.values()))} facts across "
        f"{len(harvest)} sources; reported cost ${total_cost:.2f}"
    )


if __name__ == "__main__":
    main()
