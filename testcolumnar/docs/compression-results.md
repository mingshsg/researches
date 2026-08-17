# Compression results — Elasticsearch 9.5.1

Isolated cluster `es-testcolumnar` (`http://127.0.0.1:9201`). Image `9.5.1`. Dataset: 11,964,127 NDJSON docs, **5,368,709,228 bytes** (~5.00 GiB), seed 42, path `/mnt/docker-data/testcolumnar/logs-5gb.ndjson`.

All indices: 1 shard, 0 replicas, `best_compression`, `dynamic: strict`, no `text`+`keyword` multi-fields. Force-merged to 1 segment before measurement. Field queries (`term` / `range` / `match` / ES|QL) passed on every ingested index.

## Config validation (before ingest)

| Scenario | Requested | Result |
|----------|-----------|--------|
| A `logsdb` + `stored` + `text` | accepted | `source_mode=stored` |
| B `logsdb` + `disabled` | **rejected** | `_source can not be disabled in index using [logsdb] index mode` |
| C `logsdb_columnar` + `columnar_stored` + `text` | accepted | objects auto-flattened to leaves (`host.name`) |
| D `logsdb_columnar` + `disabled` | **rejected** | supported values: `SYNTHETIC`, `COLUMNAR_STORED` |
| F `standard` + `stored` + `text` | accepted | Basic stored vs disabled pair |
| G `standard` + `disabled` + `text` | accepted | `_source` not returned; field queries still work |
| E on **basic** `logsdb_columnar` + `synthetic` + `pattern_text` | create 200 | **silently stored as `COLUMNAR_STORED`**, not synthetic |
| E on **trial** same settings | accepted | `source_mode=synthetic`, `message=pattern_text` |

`index.mapping.synthetic_source_keep` is **not allowed** on `logsdb_columnar`.

## Store size after `_forcemerge?max_num_segments=1`

| Index | License | mode | `_source` | message | pri.store | vs raw | ratio |
|-------|---------|------|-----------|---------|-----------|--------|-------|
| test-standard-stored | basic | standard | stored | text | 2,326,956,258 (2.17 GiB) | 43.3% | 2.307× |
| test-logsdb-stored | basic | logsdb | stored | text | 2,180,349,945 (2.03 GiB) | 40.6% | 2.462× |
| test-logsdb-columnar-stored | basic | logsdb_columnar | columnar_stored | text | 1,566,233,487 (1.46 GiB) | 29.2% | 3.428× |
| test-standard-disabled | basic | standard | disabled | text | 1,503,967,598 (1.40 GiB) | 28.0% | 3.570× |
| test-logsdb-columnar-synthetic | trial | logsdb_columnar | synthetic | pattern_text | 736,018,173 (0.69 GiB) | 13.7% | 7.294× |

## `_disk_usage` breakdown (bytes)

| Index | stored_fields | doc_values | inverted_index | points |
|-------|---------------|------------|----------------|--------|
| standard stored | 925,690,997 | 600,321,017 | 624,238,933 | 155,155,614 |
| logsdb stored | 921,074,538 | 547,732,990 | 582,931,489 | 126,382,384 |
| logsdb_columnar columnar_stored | 0 | 1,360,455,799 | 205,530,024 | 0 |
| standard disabled | 101,743,036 | 600,557,970 | 625,322,695 | 155,170,045 |
| logsdb_columnar synthetic + pattern_text | 0 | 576,616,189 | 159,017,425 | 0 |

## How to read this

- On **Basic**, `logsdb` cannot disable `_source`; `logsdb_columnar` cannot use `stored` or `disabled`. The only Basic stored vs disabled comparison is **standard**.
- Disabling `_source` on standard (1.40 GiB) beats Basic `logsdb_columnar`+`columnar_stored` (1.46 GiB) on this dataset, because columnar_stored still keeps a columnar copy of source in doc values (~1.36 GiB).
- **Trial synthetic + `pattern_text`** is the smallest: 0.69 GiB, **7.29×** vs raw, **2.96×** smaller than logsdb stored, **2.13×** smaller than columnar_stored.
- Users can query individual fields in all ingested modes. `message` is `text` (Basic) or `pattern_text` (trial). No `.keyword` subfield on `message`.
