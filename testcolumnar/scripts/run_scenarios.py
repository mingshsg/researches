#!/usr/bin/env python3
"""Run the compression comparison scenarios."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path("/root/testcolumnar")
SCRIPTS = ROOT / "scripts"
MAPPINGS = ROOT / "mappings"
TEMPLATES = ROOT / "templates"
RESULTS = ROOT / "results"

SCENARIOS = {
    "A": {
        "index": "test-logsdb-stored",
        "settings": TEMPLATES / "logsdb-stored.json",
        "mappings": MAPPINGS / "logs-text.json",
        "license": "basic",
    },
    "B": {
        "index": "test-logsdb-disabled",
        "settings": TEMPLATES / "logsdb-disabled.json",
        "mappings": MAPPINGS / "logs-text.json",
        "license": "basic",
    },
    "C": {
        "index": "test-logsdb-columnar-stored",
        "settings": TEMPLATES / "logsdb-columnar-stored.json",
        "mappings": MAPPINGS / "logs-text.json",
        "license": "basic",
    },
    "D": {
        "index": "test-logsdb-columnar-disabled",
        "settings": TEMPLATES / "logsdb-columnar-disabled.json",
        "mappings": MAPPINGS / "logs-text.json",
        "license": "basic",
    },
    "F": {
        "index": "test-standard-stored",
        "settings": TEMPLATES / "standard-stored.json",
        "mappings": MAPPINGS / "logs-text.json",
        "license": "basic",
    },
    "G": {
        "index": "test-standard-disabled",
        "settings": TEMPLATES / "standard-disabled.json",
        "mappings": MAPPINGS / "logs-text.json",
        "license": "basic",
    },
    "E": {
        "index": "test-logsdb-columnar-synthetic",
        "settings": TEMPLATES / "logsdb-columnar-synthetic.json",
        "mappings": MAPPINGS / "logs-pattern-text.json",
        "license": "trial",
    },
}


def run(cmd: list[str]) -> subprocess.CompletedProcess:
    print("+", " ".join(cmd), flush=True)
    return subprocess.run(cmd, check=False)


def create_validate(sc: dict, recreate: bool) -> dict:
    cmd = [
        sys.executable,
        str(SCRIPTS / "create_and_validate.py"),
        "--index",
        sc["index"],
        "--settings",
        str(sc["settings"]),
        "--mappings",
        str(sc["mappings"]),
    ]
    if recreate:
        cmd.append("--recreate")
    proc = subprocess.run(cmd, check=False, capture_output=True, text=True)
    print(proc.stdout)
    if proc.stderr:
        print(proc.stderr, file=sys.stderr)
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {"ok": False, "error": proc.stdout or proc.stderr, "returncode": proc.returncode}


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--scenarios", default="A,B,C,D,F,G")
    p.add_argument("--file", default="/mnt/docker-data/testcolumnar/logs-5gb.ndjson")
    p.add_argument("--recreate", action="store_true")
    p.add_argument("--skip-ingest", action="store_true")
    args = p.parse_args()
    RESULTS.mkdir(parents=True, exist_ok=True)
    raw_bytes = Path(args.file).stat().st_size
    summary = {"raw_bytes": raw_bytes, "scenarios": {}}
    for key in args.scenarios.split(","):
        key = key.strip()
        sc = SCENARIOS[key]
        print(f"\n===== scenario {key} {sc['index']} =====", flush=True)
        report = create_validate(sc, args.recreate)
        summary["scenarios"][key] = {"create": report}
        if not report.get("ok") and not report.get("created", True):
            print(f"scenario {key} index create/validation failed; skipping ingest")
            continue
        if not report.get("ok"):
            print(f"scenario {key} validation issues: {report.get('issues') or report.get('error')}")
            if report.get("created") is False:
                continue
            # still skip ingest if config is invalid
            continue
        if args.skip_ingest:
            continue
        ing = run(
            [
                sys.executable,
                str(SCRIPTS / "ingest.py"),
                "--index",
                sc["index"],
                "--file",
                args.file,
                "--finalize",
            ]
        )
        if ing.returncode != 0:
            summary["scenarios"][key]["ingest_failed"] = True
            continue
        run(
            [
                sys.executable,
                str(SCRIPTS / "measure.py"),
                "--index",
                sc["index"],
                "--raw-bytes",
                str(raw_bytes),
            ]
        )
        run([sys.executable, str(SCRIPTS / "validate_queries.py"), "--index", sc["index"]])
    (RESULTS / "run-summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
