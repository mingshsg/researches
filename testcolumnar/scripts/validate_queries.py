#!/usr/bin/env python3
"""Validate per-field queries. Source may be stored or disabled."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from esutil import must, request  # noqa: E402


def count_query(index: str, query: dict) -> int:
    return must("POST", f"/{index}/_count", {"query": query})["count"]


def validate(index: str) -> dict:
    total = must("GET", f"/{index}/_count")["count"]
    checks = []

    def check(name: str, query: dict, expect_positive: bool = True) -> None:
        n = count_query(index, query)
        ok = (n > 0) if expect_positive else True
        checks.append({"name": name, "count": n, "ok": ok, "query": query})

    check("term host.name", {"term": {"host.name": "web-01"}})
    check("term log.level", {"term": {"log.level": "ERROR"}})
    check("term http.method", {"term": {"http.request.method": "GET"}})
    check("term status 404", {"term": {"http.response.status_code": 404}})
    check("range timestamp", {"range": {"@timestamp": {"gte": "2026-08-01"}}})
    check("term source.ip type", {"exists": {"field": "source.ip"}})
    check("match message", {"match": {"message": "timeout"}})
    check("term service.name", {"term": {"service.name": "checkout-api"}})

    # _source presence
    search = must(
        "POST",
        f"/{index}/_search",
        {"size": 1, "query": {"match_all": {}}, "_source": True},
    )
    hit = search["hits"]["hits"][0] if search["hits"]["hits"] else {}
    src = hit.get("_source")
    source_mode = must("GET", f"/{index}/_settings")[index]["settings"]["index"]
    actual_source = ((source_mode.get("mapping") or {}).get("source") or {}).get("mode", "stored")
    if str(actual_source).lower() == "disabled":
        source_ok = not src
    else:
        # logsdb nested objects vs logsdb_columnar flattened leaves
        has_message = bool(src) and ("message" in src)
        has_host = bool(src) and ("host" in src or "host.name" in src)
        source_ok = has_message and has_host

    # ES|QL field query
    esql_status, esql = request(
        "POST",
        "/_query",
        {
            "query": f'FROM {index} | WHERE host.name == "web-01" | KEEP @timestamp, host.name, message | LIMIT 5'
        },
    )
    esql_ok = esql_status < 300 and len((esql or {}).get("values") or []) > 0

    mapping = must("GET", f"/{index}/_mapping")[index]["mappings"]["properties"]
    from esutil import find_duplicates

    dup = find_duplicates(mapping)

    report = {
        "index": index,
        "docs": total,
        "source_mode": actual_source,
        "source_returned": bool(src),
        "source_keys": sorted(src.keys()) if isinstance(src, dict) else type(src).__name__,
        "source_ok": source_ok,
        "esql_ok": esql_ok,
        "esql_status": esql_status,
        "duplicates": dup,
        "checks": checks,
        "ok": source_ok and esql_ok and not dup and all(c["ok"] for c in checks) and total > 0,
    }
    Path("/root/testcolumnar/results").mkdir(parents=True, exist_ok=True)
    Path(f"/root/testcolumnar/results/{index}-queries.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    return report


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--index", required=True)
    args = p.parse_args()
    report = validate(args.index)
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
