"""The ONE V1 command surface: `lwm <op>` (via bin/lwm in lwm-pipeline).

Every operation prints human output; `--json` prints the machine-readable
form the Phase 2 UI consumes. State is always derived from the canonical
files — nothing is stored here.
"""

import argparse
import json
import sys

from backend.lwm import episode as ep
from backend.lwm import manifest, orchestrate


def _print(data, as_json: bool):
    if as_json:
        print(json.dumps(data, indent=1, ensure_ascii=False))
        return
    if isinstance(data, dict):
        for k, v in data.items():
            if isinstance(v, (list, dict)):
                print(f"{k}: {json.dumps(v, ensure_ascii=False)[:200]}")
            else:
                print(f"{k}: {v}")
    else:
        print(data)


def main(argv=None) -> int:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--json", action="store_true", help="machine-readable output")
    common.add_argument("--episode", help="episode slug (default: the active pointer)")
    ap = argparse.ArgumentParser(prog="lwm", parents=[common],
                                 description="Lost With Maz V1 control surface")
    sub = ap.add_subparsers(dest="op", required=True)

    p_new = sub.add_parser("new", parents=[common], help="create a new episode")
    p_new.add_argument("idea", nargs="?", default="", help="topic/idea text (optional when sources given)")
    p_new.add_argument("--source", action="append", default=[],
                       help="seed source: YouTube/web URL, file path, or note text (repeatable)")
    p_new.add_argument("--offline", action="store_true", help="skip network metadata lookups")

    p_add = sub.add_parser("add-source", parents=[common], help="add source(s) to the active episode")
    p_add.add_argument("source", nargs="+", help="URL, file path, or note text")
    p_add.add_argument("--offline", action="store_true")

    sub.add_parser("status", parents=[common], help="episode status (macro state, next action, sources, artifacts)")
    p_cont = sub.add_parser("continue", parents=[common], help="run internal work until the next Maz touchpoint")
    p_cont.add_argument("--max-steps", type=int, default=6)

    p_hand = sub.add_parser("handoff", parents=[common], help="RA job -> episode (registry + briefing); internal op")
    p_hand.add_argument("job_id")
    p_hand.add_argument("--docs-dir", help="local doc_0/1/2.json dir (offline/testing)")

    p_chk = sub.add_parser("check-script", parents=[common], help="stage 10b final script fact-check (D-SFC-1)")
    p_chk.add_argument("script", nargs="?", help="script path (default: episode 07-draft.md)")

    p_pkg = sub.add_parser("package", parents=[common], help="stage 11 production package from the locked script")
    p_pkg.add_argument("script", nargs="?", help="script path (default: episode 07-draft.md)")

    sub.add_parser("research", parents=[common], help="run a Research Agent round now (internal op)")

    p_dec = sub.add_parser("decide", parents=[common],
                           help="record a Maz touchpoint decision (A/B/C/D)")
    p_dec.add_argument("touchpoint", choices=["A", "B", "C", "D"])
    p_dec.add_argument("--angle", default="")
    p_dec.add_argument("--packaging", default="")
    p_dec.add_argument("--format", dest="format_", default="")
    p_dec.add_argument("--kill", action="store_true")
    p_dec.add_argument("--notes", default="")
    p_dec.add_argument("--waive", action="store_true")
    p_dec.add_argument("--approve", action="store_true")
    p_dec.add_argument("--correction", default="")
    p_dec.add_argument("--corrections", default="")

    args = ap.parse_args(argv)

    if args.op == "new":
        result = ep.create(args.idea, sources=args.source, offline=args.offline)
        _print(result, args.json)
    elif args.op == "add-source":
        episode = ep.resolve(args.episode)
        results = [manifest.add_source(episode, s, offline=args.offline) for s in args.source]
        _print({"episode": episode.name, "added": results}, args.json)
    elif args.op == "status":
        _print(ep.status(args.episode), args.json)
    elif args.op == "continue":
        log = orchestrate.step(args.episode, max_steps=args.max_steps)
        _print({"log": log}, args.json)
        stop = next((e["stop"] for e in log if "stop" in e), None)
        if stop and not args.json:
            print(f"\nSTOPPED: {stop['reason']} — {stop['detail']}")
    elif args.op == "handoff":
        from pathlib import Path

        from backend.lwm import handoff as h
        episode = ep.resolve(args.episode)
        result = h.run_handoff(episode, args.job_id,
                               docs_dir=Path(args.docs_dir) if args.docs_dir else None)
        _print(result, args.json)
    elif args.op == "check-script":
        from pathlib import Path

        from backend.config import get_settings
        from backend.integrations.structured_client import get_structured_client
        from backend.lwm import decisions, factcheck
        episode = ep.resolve(args.episode)
        locked = decisions.locked_script(episode)
        script = Path(args.script) if args.script else (locked[0] if locked else episode / "07-draft.md")
        client = get_structured_client(get_settings().model_judge)
        report = factcheck.run(script, episode, client,
                               lb_claims=factcheck.load_bearing_claims(episode))
        _print({k: report[k] for k in ("claims_checked", "counts", "material_findings", "blocks_recording")}, args.json)
    elif args.op == "package":
        from pathlib import Path

        from backend.lwm import decisions, production
        episode = ep.resolve(args.episode)
        locked = decisions.locked_script(episode)
        script = Path(args.script) if args.script else (locked[0] if locked else episode / "07-draft.md")
        result = production.build(episode, script)
        _print({"beats": len(result["beats"]), "claims": len(result["claims_ledger"]),
                "load_bearing": len(result["load_bearing"])}, args.json)
    elif args.op == "decide":
        from backend.lwm import decisions
        episode = ep.resolve(args.episode)
        if args.touchpoint == "A":
            result = decisions.decide_a(episode, args.angle, args.packaging,
                                        args.format_, kill=args.kill)
        elif args.touchpoint == "B":
            result = decisions.decide_b(episode, notes=args.notes, waive=args.waive)
        elif args.touchpoint == "C":
            result = decisions.decide_c(episode, approve=args.approve,
                                        correction=args.correction)
        else:
            result = decisions.decide_d(episode, approve=args.approve,
                                        corrections=args.corrections)
        _print(result, args.json)
    elif args.op == "research":
        from backend.lwm import research
        episode = ep.resolve(args.episode)
        topic = ep.status(episode.name)["topic"]
        result = research.run_round(episode, topic)
        research.run_gap_rounds(episode, topic)
        _print(result, args.json)
    return 0


if __name__ == "__main__":
    sys.exit(main())
