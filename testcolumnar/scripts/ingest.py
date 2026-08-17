#!/usr/bin/env python3
"""Bulk-ingest NDJSON into an existing Elasticsearch index."""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from esutil import must, request  # noqa: E402


def ingest(index: str, ndjson_path: str, batch_docs: int) -> dict:
    status, _ = request("GET", f"/{index}")
    if status != 200:
        raise RuntimeError(f"refusing to ingest: index {index} does not exist (avoid bulk auto-create)")
    action = json.dumps({"index": {}}).encode("utf-8") + b"\n"
    sent = 0
    errors = 0
    t0 = time.time()
    buf = bytearray()
    nbuf = 0
    with open(ndjson_path, "rb") as fh:
        for line in fh:
            if not line.strip():
                continue
            buf.extend(action)
            buf.extend(line if line.endswith(b"\n") else line + b"\n")
            nbuf += 1
            if nbuf >= batch_docs:
                nerr = _flush(index, buf)
                errors += nerr
                sent += nbuf
                buf.clear()
                nbuf = 0
                if nerr:
                    raise RuntimeError(f"bulk failed with {nerr} item errors after {sent} docs")
                if sent % (batch_docs * 20) == 0:
                    elapsed = time.time() - t0
                    rate = sent / elapsed if elapsed else 0
                    print(f"ingested {sent} docs, {rate:.0f} docs/s, errors={errors}", flush=True)
        if nbuf:
            errors += _flush(index, buf)
            sent += nbuf
    elapsed = time.time() - t0
    return {"docs_sent": sent, "errors": errors, "seconds": round(elapsed, 1)}


def _flush(index: str, buf: bytearray) -> int:
    status, payload = request("POST", f"/{index}/_bulk", bytes(buf), timeout=300)
    if status >= 300:
        raise RuntimeError(f"bulk failed {status}: {json.dumps(payload)[:1000]}")
    if payload.get("errors"):
        n = sum(1 for item in payload.get("items", []) if "error" in item.get("index", {}))
        if n:
            sample = next(
                item["index"]["error"]
                for item in payload.get("items", [])
                if "error" in item.get("index", {})
            )
            print(f"bulk item errors={n} sample={sample}", flush=True)
        return n
    return 0


def finalize(index: str) -> dict:
    must("POST", f"/{index}/_refresh")
    merge = must("POST", f"/{index}/_forcemerge?max_num_segments=1", timeout=3600)
    must("POST", f"/{index}/_refresh")
    count = must("GET", f"/{index}/_count")
    return {"forcemerge": merge, "count": count.get("count")}


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--index", required=True)
    p.add_argument("--file", required=True)
    p.add_argument("--batch-docs", type=int, default=4000)
    p.add_argument("--finalize", action="store_true")
    args = p.parse_args()
    stats = ingest(args.index, args.file, args.batch_docs)
    if args.finalize:
        stats["finalize"] = finalize(args.index)
    print(json.dumps(stats, indent=2))
    return 0 if stats["errors"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
