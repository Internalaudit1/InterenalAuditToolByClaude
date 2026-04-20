#!/bin/sh
set -eu

export PATH="/opt/venv/bin:$PATH"

mkdir -p /app/storage/uploads /run/nginx

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

exec /usr/bin/supervisord -n -c /etc/supervisor/supervisord.conf
