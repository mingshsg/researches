#!/usr/bin/env python3
"""Create an index and validate settings/mappings before ingest."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from esutil import find_duplicates, load_json, must, request  # noqa: E402

ROOT = Path("/root/testcolumnar")
SAMPLE = ROOT / "data" / "sample.ndjson"


def field_exists(props: dict, dotted: str) -> bool:
    """True if mapping has nested objects or columnar flattened leaves."""
    if dotted in props:
        return True
    cur: dict | None = props
    for part in dotted.split("."):
        if not cur or part not in cur:
            return False
        spec = cur[part]
        cur = spec.get("properties")
    return True


def expected_source(mode: str) -> set[str]:
    return {mode.lower(), mode.upper()}


def validate_created(index: str, expected: dict) -> dict:
    settings = must("GET", f"/{index}/_settings")[index]["settings"]["index"]
    mappings = must("GET", f"/{index}/_mapping")[index]["mappings"]
    props = mappings.get("properties") or {}
    issues: list[str] = []

    actual_mode = settings.get("mode")
    if actual_mode != expected["index_mode"]:
        issues.append(f"index.mode expected {expected['index_mode']}, got {actual_mode}")

    actual_source = ((settings.get("mapping") or {}).get("source") or {}).get("mode", "stored")
    if str(actual_source).lower() != expected["source_mode"].lower():
        issues.append(
            f"source.mode expected {expected['source_mode']}, got {actual_source}"
        )

    msg = ((props.get("message") or {}).get("type"))
    if msg != expected["message_type"]:
        issues.append(f"message type expected {expected['message_type']}, got {msg}")

    issues.extend(find_duplicates(props))

    if mappings.get("dynamic") != "strict":
        issues.append(f"dynamic expected strict, got {mappings.get('dynamic')}")

    required_leaves = [
        "@timestamp",
        "host.name",
        "service.name",
        "service.version",
        "log.level",
        "http.request.method",
        "http.response.status_code",
        "http.response.bytes",
        "url.path",
        "source.ip",
        "event.duration",
        "trace.id",
        "message",
    ]
    for field in required_leaves:
        if not field_exists(props, field):
            issues.append(f"missing field {field}")

    # Sample ingest + mapping stability
    if not SAMPLE.exists():
        issues.append(f"missing sample file {SAMPLE}")
        return {"ok": False, "issues": issues, "settings": settings, "mappings": mappings}

    first = SAMPLE.read_text(encoding="utf-8").splitlines()[0]
    status, payload = request("POST", f"/{index}/_doc?refresh=true", json.loads(first))
    if status >= 300:
        issues.append(f"sample ingest failed {status}: {json.dumps(payload)[:800]}")
    else:
        must("POST", f"/{index}/_delete_by_query?refresh=true&conflicts=proceed", {"query": {"match_all": {}}})

    mappings_after = must("GET", f"/{index}/_mapping")[index]["mappings"]
    if mappings_after != mappings and not issues:
        # delete_by_query should not change mapping; extra dynamic fields would
        extras = find_duplicates(mappings_after.get("properties") or {})
        issues.extend(extras)

    ok = not issues
    report = {
        "ok": ok,
        "index": index,
        "issues": issues,
        "actual": {
            "mode": actual_mode,
            "source_mode": actual_source,
            "message_type": msg,
            "dynamic": mappings.get("dynamic"),
            "codec": settings.get("codec"),
            "number_of_shards": settings.get("number_of_shards"),
            "number_of_replicas": settings.get("number_of_replicas"),
        },
    }
    return report


def create_index(index: str, settings_file: str, mappings_file: str, recreate: bool) -> dict:
    settings = load_json(settings_file)["settings"]
    mappings = load_json(mappings_file)
    status, _ = request("GET", f"/{index}")
    exists = status == 200
    if exists:
        if not recreate:
            raise RuntimeError(f"index {index} already exists; pass --recreate to replace it")
        must("DELETE", f"/{index}")
    body = {"settings": settings, "mappings": mappings}
    status, payload = request("PUT", f"/{index}", body)
    if status >= 300:
        return {
            "ok": False,
            "created": False,
            "index": index,
            "http_status": status,
            "error": payload,
        }
    expected = {
        "index_mode": settings["index.mode"],
        "source_mode": settings["index.mapping.source.mode"],
        "message_type": mappings["properties"]["message"]["type"],
    }
    report = validate_created(index, expected)
    report["created"] = True
    report["http_status"] = status
    return report


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--index", required=True)
    p.add_argument("--settings", required=True)
    p.add_argument("--mappings", required=True)
    p.add_argument("--recreate", action="store_true")
    args = p.parse_args()
    report = create_index(args.index, args.settings, args.mappings, args.recreate)
    print(json.dumps(report, indent=2))
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
