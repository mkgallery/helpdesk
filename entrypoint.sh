#!/bin/sh
set -e

echo "Waiting for the database..."
python - << 'PY'
import os, socket, time

host = os.environ.get("DB_HOST", "db")
port = int(os.environ.get("DB_PORT", "3306"))
for _ in range(60):
    try:
        socket.create_connection((host, port), timeout=2).close()
        break
    except OSError:
        time.sleep(2)
else:
    raise SystemExit("Database is not reachable")
PY

python manage.py makemigrations tickets --noinput
python manage.py migrate --noinput

# Optional: auto-create a supervisor if these variables are set
if [ -n "$DJANGO_SUPERUSER_USERNAME" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
  python manage.py createsuperuser --noinput || true
fi

exec "$@"
