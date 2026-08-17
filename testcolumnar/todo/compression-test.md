# Compression test TODO

Updated 2026-08-17.

- [x] Record plan changes (docs + chn.docs)
- [x] Generate ~5GB NDJSON test logs (11,964,127 docs)
- [x] Dedicated Elasticsearch 9.5.1 Docker `es-testcolumnar` on 9201 (Basic, then trial)
- [x] Create and validate mappings/settings per scenario
- [x] Ingest the same NDJSON into each accepted index
- [x] Force-merge, measure compression, validate field queries
- [x] Basic: logsdb stored; logsdb/columnar disabled rejected; standard stored vs disabled; logsdb_columnar columnar_stored
- [x] Trial: logsdb_columnar + synthetic + pattern_text
- [x] Write comparison report
- [x] Generate 50GB NDJSON (119,642,150 docs)
- [x] Recreate five indices, ingest 50GB, measure, query-validate
- [x] Write 50GB final report

