# Review notes

- Shared `es-bench:9200` is unsafe for this test: another runner deletes indices and may recreate/stop the container. Use `es-testcolumnar:9201`.
- Always GET settings after PUT. Requesting `synthetic` on Basic returns HTTP 200 but `source.mode` is `COLUMNAR_STORED`.
- `logsdb` and `logsdb_columnar` reject `source.mode=disabled`. Do not assume disabled `_source` is a valid logsdb knob.
- `logsdb_columnar` auto-flattens object mappings; query names stay dotted (`host.name`) but `_source` is flat.
- `pattern_text` mapping was accepted on Basic in 9.5.1; synthetic source was not. Size win in scenario E is the combination of synthetic (no columnar source copy) plus `pattern_text` (smaller inverted index / doc_values on `message`).
- Measure only after `_forcemerge?max_num_segments=1` so segment count does not skew ratios.
