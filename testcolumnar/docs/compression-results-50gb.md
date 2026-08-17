# 50 GiB final compression results — Elasticsearch 9.5.1

Cluster: `es-testcolumnar:9201`. Dataset: **119,642,150** docs, **53,687,091,267 bytes** (50.00 GiB), seed 42. Same mappings as the 5 GiB run. All five indices: 119,642,150 docs, green, force-merged, field queries passed.

## Store size

| Index | License* | mode | `_source` | message | pri.store | vs raw | ratio |
|-------|----------|------|-----------|---------|-----------|--------|-------|
| test-standard-stored | settings as Basic | standard | stored | text | 23,141,409,990 (21.55 GiB) | 43.1% | 2.320× |
| test-logsdb-stored | settings as Basic | logsdb | stored | text | 21,777,382,976 (20.28 GiB) | 40.6% | 2.465× |
| test-logsdb-columnar-stored | settings as Basic | logsdb_columnar | columnar_stored | text | 15,523,416,407 (14.46 GiB) | 28.9% | 3.458× |
| test-standard-disabled | settings as Basic | standard | disabled | text | 14,222,716,473 (13.25 GiB) | 26.5% | 3.775× |
| test-logsdb-columnar-synthetic | trial | logsdb_columnar | synthetic | pattern_text | **7,249,844,041 (6.75 GiB)** | **13.5%** | **7.405×** |

\*Cluster was on trial during the 50 GiB ingest; explicit `stored` / `columnar_stored` / `disabled` were validated after index create and did not silently become synthetic.

## vs 5 GiB run

Ratios are stable or slightly better at 50 GiB (more repetition for codec / `pattern_text` templates):

| Index | 5 GiB ratio | 50 GiB ratio |
|-------|-------------|--------------|
| standard stored | 2.307× | 2.320× |
| logsdb stored | 2.462× | 2.465× |
| logsdb_columnar columnar_stored | 3.428× | 3.458× |
| standard disabled | 3.570× | 3.775× |
| logsdb_columnar synthetic + pattern_text | 7.294× | 7.405× |

## `_disk_usage` (bytes)

| Index | stored_fields | doc_values | inverted_index | points |
|-------|---------------|------------|----------------|--------|
| standard stored | 9,256,877,308 | 5,875,417,612 | 5,939,526,717 | 1,865,895,461 |
| logsdb stored | 9,210,908,966 | 5,412,787,074 | 5,552,158,129 | 1,578,469,618 |
| logsdb_columnar columnar_stored | 0 | 13,601,423,213 | 1,920,662,568 | 0 |
| standard disabled | 336,151,802 | 5,875,439,117 | 5,917,927,556 | 1,865,872,880 |
| logsdb_columnar synthetic + pattern_text | 0 | 5,759,167,724 | 1,489,266,018 | 0 |
