#!/bin/bash
# Recreate validated indices and ingest the 50GiB NDJSON.
set -euo pipefail
export ELASTICSEARCH_URL="${ELASTICSEARCH_URL:-http://127.0.0.1:9201}"
export MEASURE_CSV=/root/testcolumnar/results/compression-50gb.csv
ROOT=/root/testcolumnar
FILE=/mnt/docker-data/testcolumnar/logs-50gb.ndjson
RAW=$(stat -c%s "$FILE")
echo "raw_bytes=$RAW file=$FILE"

create() {
  python3 "$ROOT/scripts/create_and_validate.py" --index "$1" --settings "$2" --mappings "$3" --recreate
}

echo "===== recreate A logsdb stored ====="
create test-logsdb-stored "$ROOT/templates/logsdb-stored.json" "$ROOT/mappings/logs-text.json"
echo "===== recreate C logsdb_columnar columnar_stored ====="
create test-logsdb-columnar-stored "$ROOT/templates/logsdb-columnar-stored.json" "$ROOT/mappings/logs-text.json"
echo "===== recreate F standard stored ====="
create test-standard-stored "$ROOT/templates/standard-stored.json" "$ROOT/mappings/logs-text.json"
echo "===== recreate G standard disabled ====="
create test-standard-disabled "$ROOT/templates/standard-disabled.json" "$ROOT/mappings/logs-text.json"
echo "===== recreate E columnar synthetic pattern_text ====="
create test-logsdb-columnar-synthetic "$ROOT/templates/logsdb-columnar-synthetic.json" "$ROOT/mappings/logs-pattern-text.json"

for idx in test-logsdb-stored test-logsdb-columnar-stored test-standard-stored test-standard-disabled test-logsdb-columnar-synthetic; do
  echo "===== INGEST $idx ====="
  python3 "$ROOT/scripts/ingest.py" --index "$idx" --file "$FILE" --batch-docs 8000 --finalize
  python3 "$ROOT/scripts/measure.py" --index "$idx" --raw-bytes "$RAW"
  python3 "$ROOT/scripts/validate_queries.py" --index "$idx"
done
echo ALL_50GB_DONE
