#!/bin/sh
set -e

echo "Ожидание PostgreSQL..."
i=0
while [ "$i" -lt 60 ]; do
  if python - <<'PY'
import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()
from django.db import connection
connection.ensure_connection()
PY
  then
    echo "База данных доступна."
    break
  fi
  i=$((i + 1))
  sleep 2
done

if [ "$i" -ge 60 ]; then
  echo "Не удалось подключиться к БД за 120 с." >&2
  exit 1
fi

python manage.py migrate --noinput
python manage.py collectstatic --noinput

exec gunicorn config.wsgi:application \
  --bind "0.0.0.0:${PORT:-8000}" \
  --workers "${GUNICORN_WORKERS:-3}" \
  --timeout "${GUNICORN_TIMEOUT:-120}" \
  --access-logfile - \
  --error-logfile -
