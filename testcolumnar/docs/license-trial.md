# Isolated cluster license change

Cluster: `es-testcolumnar` on port 9201 (not shared `es-bench`).

Planned change: `POST /_license/start_trial?acknowledge=true`

Purpose: enable `index.mapping.source.mode=synthetic` on `logsdb_columnar` (Basic silently falls back to `COLUMNAR_STORED`) and compare `pattern_text` with synthetic source.

Does not modify the shared `es-bench` cluster.
