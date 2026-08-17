# Isolated Elasticsearch for this project

The host already runs `es-bench` (Elasticsearch 9.5.1 on port 9200) for another benchmark
(`/mnt/docker-data/esbench`). That runner deletes indices and may `docker stop`/`docker rm -f`
the shared container.

This project starts a **dedicated** container:

- name: `es-testcolumnar`
- image: `docker.elastic.co/elasticsearch/elasticsearch:9.5.1`
- port: `9201`
- data: `/mnt/docker-data/testcolumnar/es-data`
- license: `basic` (`xpack.license.self_generated.type=basic`)
- security: disabled (local lab)
- heap: 4g

Do not stop or remove `es-bench`.
