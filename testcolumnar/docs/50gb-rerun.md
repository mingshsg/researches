# 50 GiB final rerun

Same mappings and index settings as the 5 GiB run, on `es-testcolumnar:9201`.

- Input: `/mnt/docker-data/testcolumnar/logs-50gb.ndjson` (generated, seed 42)
- Recreate the five accepted test indices (Elasticsearch indices only; keep the 5 GiB NDJSON file)
- Measure into `results/compression-50gb.csv`
- Trial license is already active; validate that explicit `stored` / `columnar_stored` / `disabled` are not silently changed to synthetic
