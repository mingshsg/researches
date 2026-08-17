#!/bin/bash
# Start a dedicated ES 9.5.1 for this project. Does not touch es-bench.
set -euo pipefail
NAME=es-testcolumnar
DATA=/mnt/docker-data/testcolumnar/es-data
mkdir -p "$DATA"
chown -R 1000:1000 "$DATA" || true
if docker inspect "$NAME" >/dev/null 2>&1; then
  echo "container $NAME already exists; leaving it running"
else
  docker run -d \
    --name "$NAME" \
    -p 9201:9200 \
    -v "$DATA:/usr/share/elasticsearch/data" \
    -e "ES_JAVA_OPTS=-Xms4g -Xmx4g" \
    -e "bootstrap.memory_lock=false" \
    -e "cluster.routing.allocation.disk.threshold_enabled=false" \
    -e "xpack.security.enabled=false" \
    -e "xpack.security.http.ssl.enabled=false" \
    -e "xpack.security.transport.ssl.enabled=false" \
    -e "xpack.license.self_generated.type=basic" \
    -e "discovery.type=single-node" \
    docker.elastic.co/elasticsearch/elasticsearch:9.5.1
fi
for i in $(seq 1 120); do
  if curl -sf http://127.0.0.1:9201 >/dev/null; then
    echo "ES ready on 9201"
    curl -sf http://127.0.0.1:9201/_license?pretty | head -n 20
    exit 0
  fi
  sleep 2
done
echo "ES did not become ready"
exit 1
