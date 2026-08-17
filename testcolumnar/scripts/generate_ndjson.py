#!/usr/bin/env python3
"""Generate deterministic HTTP/application NDJSON logs."""
from __future__ import annotations

import argparse
import os
import random
from datetime import datetime, timedelta, timezone

HOSTS = [f"web-{i:02d}" for i in range(1, 25)]
SERVICES = [
    ("checkout-api", "1.8.2"),
    ("auth-api", "2.1.0"),
    ("catalog-api", "3.4.1"),
    ("payments-api", "1.2.9"),
    ("inventory-api", "4.0.3"),
]
LEVELS = ["INFO", "INFO", "INFO", "INFO", "WARN", "ERROR"]
METHODS = ["GET", "GET", "GET", "POST", "PUT", "DELETE"]
PATHS = [
    "/api/v1/orders",
    "/api/v1/orders/{id}",
    "/api/v1/users/{id}",
    "/api/v1/cart",
    "/api/v1/payments",
    "/health",
    "/api/v1/inventory/sku/{id}",
    "/api/v1/search",
]
STATUSES = [200, 200, 200, 200, 201, 204, 400, 401, 404, 500, 502, 503]
TEMPLATES = [
    "Request completed method={method} path={path} status={status} duration={duration_ms}ms bytes={bytes}",
    "Failed to fetch user id={user_id} from cache reason={reason}",
    "Database query finished table={table} rows={rows} elapsed={duration_ms}ms",
    "Auth token validated user={user_id} client={client}",
    "Upstream timeout service={upstream} attempt={attempt} of 3 path={path}",
    "Rate limit exceeded key={user_id} method={method} path={path} retry_after={retry_after}s",
    "Cache miss key={cache_key} store=redis ttl={ttl}s",
    "Payment authorized order={order_id} amount_cents={amount} processor=stripe",
]


def iso(ts: datetime) -> str:
    return ts.strftime("%Y-%m-%dT%H:%M:%S.") + f"{ts.microsecond // 1000:03d}Z"


def one_doc(rng: random.Random, ts: datetime) -> str:
    host = rng.choice(HOSTS)
    service, version = rng.choice(SERVICES)
    level = rng.choice(LEVELS)
    method = rng.choice(METHODS)
    path = rng.choice(PATHS).replace("{id}", str(rng.randint(1000, 999999)))
    status = rng.choice(STATUSES)
    duration_ms = rng.randint(1, 2500)
    nbytes = rng.randint(200, 180000)
    ip = f"10.{rng.randint(0, 20)}.{rng.randint(0, 255)}.{rng.randint(1, 254)}"
    trace = f"{rng.getrandbits(64):016x}{rng.getrandbits(64):016x}"
    user_id = rng.randint(10000, 99999)
    tmpl = rng.choice(TEMPLATES)
    message = tmpl.format(
        method=method,
        path=path,
        status=status,
        duration_ms=duration_ms,
        bytes=nbytes,
        user_id=user_id,
        reason=rng.choice(["timeout", "not_found", "stale"]),
        table=rng.choice(["orders", "users", "payments", "cart_items"]),
        rows=rng.randint(0, 500),
        client=rng.choice(["ios", "android", "web"]),
        upstream=rng.choice(["catalog-api", "payments-api", "auth-api"]),
        attempt=rng.randint(1, 3),
        retry_after=rng.randint(1, 30),
        cache_key=f"user:{user_id}:profile",
        ttl=rng.choice([30, 60, 120, 300]),
        order_id=f"ord-{rng.randint(100000, 999999)}",
        amount=rng.randint(199, 99999),
    )
    # Compact JSON; field set is fixed for strict mappings.
    return (
        "{"
        f'"@timestamp":"{iso(ts)}",'
        f'"host":{{"name":"{host}"}},'
        f'"service":{{"name":"{service}","version":"{version}"}},'
        f'"log":{{"level":"{level}"}},'
        f'"http":{{"request":{{"method":"{method}"}},'
        f'"response":{{"status_code":{status},"bytes":{nbytes}}}}},'
        f'"url":{{"path":"{path}"}},'
        f'"source":{{"ip":"{ip}"}},'
        f'"event":{{"duration":{duration_ms * 1_000_000}}},'
        f'"trace":{{"id":"{trace}"}},'
        f'"message":"{message}"'
        "}\n"
    )


def generate(path: str, target_bytes: int, seed: int, sample_path: str | None) -> dict:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    rng = random.Random(seed)
    ts = datetime(2026, 8, 1, tzinfo=timezone.utc)
    written = 0
    docs = 0
    sample_lines: list[str] = []
    with open(path, "w", encoding="utf-8") as fh:
        while written < target_bytes:
            ts += timedelta(milliseconds=rng.randint(1, 40))
            line = one_doc(rng, ts)
            fh.write(line)
            written += len(line.encode("utf-8"))
            docs += 1
            if len(sample_lines) < 200:
                sample_lines.append(line)
            if docs % 500_000 == 0:
                print(f"generated {docs} docs, {written / (1024**3):.2f} GiB", flush=True)
    if sample_path:
        os.makedirs(os.path.dirname(sample_path), exist_ok=True)
        with open(sample_path, "w", encoding="utf-8") as sf:
            sf.writelines(sample_lines)
    return {"path": path, "bytes": written, "docs": docs, "sample_path": sample_path}


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--out", default="/mnt/docker-data/testcolumnar/logs-5gb.ndjson")
    p.add_argument("--sample", default="/root/testcolumnar/data/sample.ndjson")
    p.add_argument("--bytes", type=int, default=5 * 1024 * 1024 * 1024)
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args()
    stats = generate(args.out, args.bytes, args.seed, args.sample)
    print(stats)


if __name__ == "__main__":
    main()
