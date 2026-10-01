#!/bin/bash
# Integration tests: a real Flask app (tests/test_server.py) + real Postgres, no mocks.
set -e
cd "$(dirname "$0")"

echo "Starting test stack..."
docker compose -f docker-compose.test.yml up -d --build

echo "Waiting for API..."
for i in {1..60}; do
  if curl -s -o /dev/null -w "%{http_code}" http://localhost:5098/health 2>/dev/null | grep -q 200; then
    echo "API ready."
    break
  fi
  [ $i -eq 60 ] && { echo "API failed."; docker compose -f docker-compose.test.yml logs api | tail -30; docker compose -f docker-compose.test.yml down; exit 1; }
  sleep 1
done

set +e
# pytest runs inside the api container (its dev deps are installed there),
# against the app served in that same container.
docker compose -f docker-compose.test.yml exec -T -e FLASK_CORE_TEST_API_URL=http://localhost:5000 api pytest -v
EXIT_CODE=$?

docker compose -f docker-compose.test.yml down
echo "Done."
exit $EXIT_CODE
