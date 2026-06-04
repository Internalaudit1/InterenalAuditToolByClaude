#!/bin/sh
set -eu

export PATH="/opt/venv/bin:/usr/local/bin:$PATH"
export NODE_ENV="${NODE_ENV:-production}"

mkdir -p /app/storage/uploads

cd /app/apps/api

python - <<'PY'
import os
import time

from sqlalchemy import create_engine, text

database_url = os.environ["API_DATABASE_URL"]
print("Waiting for configured PostgreSQL database...")
for attempt in range(60):
    try:
        engine = create_engine(database_url, future=True, pool_pre_ping=True)
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        print("Database connection ready.")
        break
    except Exception as exc:  # pragma: no cover - container runtime script
        if attempt == 59:
            raise
        print(f"Database not ready yet ({attempt + 1}/60): {exc}")
        time.sleep(2)
PY

alembic upgrade head

if [ "${API_RUN_SEED_ON_STARTUP:-false}" = "true" ]; then
  python -m app.db.seed
else
  echo "Skipping seed startup flow."
fi

cd /app/apps/api
uvicorn app.main:app --host 127.0.0.1 --port 8000 &
API_PID=$!

if [ -f /app/apps/web/.next/standalone/apps/web/server.js ]; then
  cd /app/apps/web/.next/standalone/apps/web
  HOSTNAME=127.0.0.1 PORT=3100 node server.js &
else
  cd /app
  npm --workspace apps/web run start -- --hostname 127.0.0.1 --port 3100 &
fi
WEB_PID=$!

node /app/proxy.mjs &
PROXY_PID=$!

cleanup() {
  for pid in "$PROXY_PID" "$WEB_PID" "$API_PID"; do
    kill "$pid" 2>/dev/null || true
  done
  wait "$PROXY_PID" "$WEB_PID" "$API_PID" 2>/dev/null || true
}

trap cleanup INT TERM

while :; do
  for pid in "$PROXY_PID" "$WEB_PID" "$API_PID"; do
    if ! kill -0 "$pid" 2>/dev/null; then
      wait "$pid" || true
      cleanup
      exit 1
    fi
  done
  sleep 2
done
