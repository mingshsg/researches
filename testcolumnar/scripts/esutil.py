#!/usr/bin/env python3
"""Elasticsearch helpers for the compression test."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

ES_URL = os.environ.get("ELASTICSEARCH_URL", "http://127.0.0.1:9201").rstrip("/")


def request(method: str, path: str, body: Any = None, timeout: int = 600) -> tuple[int, Any]:
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        if isinstance(body, (bytes, bytearray)):
            data = bytes(body)
            headers["Content-Type"] = "application/x-ndjson"
        else:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
    req = urllib.request.Request(ES_URL + path, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            if not raw:
                return resp.status, {}
            return resp.status, json.loads(raw.decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            parsed = {"error": raw}
        return exc.code, parsed


def must(method: str, path: str, body: Any = None, timeout: int = 600) -> Any:
    status, payload = request(method, path, body, timeout=timeout)
    if status >= 300:
        raise RuntimeError(f"{method} {path} -> {status}: {json.dumps(payload)[:2000]}")
    return payload


def load_json(path: str) -> Any:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def walk_properties(props: dict, prefix: str = "") -> list[tuple[str, dict]]:
    out: list[tuple[str, dict]] = []
    for name, spec in props.items():
        path = f"{prefix}.{name}" if prefix else name
        out.append((path, spec))
        if "properties" in spec:
            out.extend(walk_properties(spec["properties"], path))
    return out


def find_duplicates(props: dict) -> list[str]:
    bad: list[str] = []
    for path, spec in walk_properties(props):
        fields = spec.get("fields") or {}
        ftype = spec.get("type")
        if ftype in {"text", "pattern_text"} and "keyword" in fields:
            bad.append(f"{path} has text/pattern_text + keyword multi-field")
        if ftype == "keyword" and "text" in fields:
            bad.append(f"{path} has keyword + text multi-field")
    return bad
