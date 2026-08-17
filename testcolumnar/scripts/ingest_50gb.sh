#!/bin/bash
# 50GiB ingest only (indices must already exist and be empty/validated).
set -euo pipefail
export ELASTICSEARCH_URL="${ELASTICSEARCH_URL:-http://127.0.0.1:9201}"
export MEASURE_CSV=/root/testcolumnar/results/compression-50gb.csv
ROOT=/root/testcolumnar
FILE=/mnt/docker-data/testcolumnar/logs-50gb.ndjson
RAW=$(stat -c%s "$FILE")
echo "raw_bytes=$RAW start=$(date -u +%FT%TZ)"
for idx in test-logsdb-stored test-logsdb-columnar-stored test-standard-stored test-standard-disabled test-logsdb-columnar-synthetic; do
  echo "===== INGEST $idx ====="
  python3 "$ROOT/scripts/ingest.py" --index "$idx" --file "$FILE" --batch-docs 8000 --finalize
  python3 "$ROOT/scripts/measure.py" --index "$idx" --raw-bytes "$RAW"
  python3 "$ROOT/scripts/validate_queries.py" --index "$idx"
done
echo ALL_50GB_DONE
echo "end=$(date -u +%FT%TZ)"
