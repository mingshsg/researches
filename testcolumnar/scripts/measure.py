#!/usr/bin/env python3
"""Measure store size and per-field disk usage after forcemerge."""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from esutil import must  # noqa: E402

RESULTS = Path("/root/testcolumnar/results")


def measure(index: str, raw_bytes: int) -> dict:
    cat = must(
        "GET",
        f"/_cat/indices/{index}?format=json&bytes=b&h=index,docs.count,pri.store.size,store.size",
    )[0]
    store_bytes = int(cat["pri.store.size"])
    docs = int(cat["docs.count"])
    disk = must("POST", f"/{index}/_disk_usage?run_expensive_tasks=true&flush=true")
    idx_disk = disk.get(index) or disk[next(iter(k for k in disk if k not in {'_shards'}))]
    all_fields = idx_disk["all_fields"]
    inv = all_fields.get("inverted_index")
    if isinstance(inv, dict):
        inverted_bytes = inv.get("total_in_bytes")
    else:
        inverted_bytes = all_fields.get("inverted_index_in_bytes")
    ratio = (raw_bytes / store_bytes) if store_bytes else None
    row = {
        "index": index,
        "docs": docs,
        "raw_bytes": raw_bytes,
        "pri_store_bytes": store_bytes,
        "compression_ratio": round(ratio, 3) if ratio else None,
        "stored_fields_bytes": all_fields.get("stored_fields_in_bytes"),
        "doc_values_bytes": all_fields.get("doc_values_in_bytes"),
        "inverted_index_bytes": inverted_bytes,
        "points_bytes": all_fields.get("points_in_bytes"),
        "cat": cat,
        "all_fields": all_fields,
        "fields": idx_disk.get("fields"),
    }
    RESULTS.mkdir(parents=True, exist_ok=True)
    out = RESULTS / f"{index}-disk.json"
    out.write_text(json.dumps(row, indent=2), encoding="utf-8")
    csv_path = Path(os.environ.get("MEASURE_CSV", str(RESULTS / "compression.csv")))
    write_header = not csv_path.exists()
    with csv_path.open("a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(
            fh,
            fieldnames=[
                "index",
                "docs",
                "raw_bytes",
                "pri_store_bytes",
                "compression_ratio",
                "stored_fields_bytes",
                "doc_values_bytes",
                "inverted_index_bytes",
                "points_bytes",
            ],
        )
        if write_header:
            w.writeheader()
        w.writerow({k: row[k] for k in w.fieldnames})
    return row


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--index", required=True)
    p.add_argument("--raw-bytes", type=int, required=True)
    args = p.parse_args()
    row = measure(args.index, args.raw_bytes)
    slim = {k: row[k] for k in row if k not in {"fields", "all_fields", "cat"}}
    print(json.dumps(slim, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
