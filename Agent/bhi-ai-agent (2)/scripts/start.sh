#!/bin/sh
set -e

mkdir -p /app/data/personal /app/exports

if [ -n "$STAFF_JSON_B64" ]; then
  echo "$STAFF_JSON_B64" | base64 -d > /app/data/staff.json
  echo "[start] staff.json restored from STAFF_JSON_B64"
fi

if [ -n "$PERSONAL_JSON_B64" ]; then
  echo "$PERSONAL_JSON_B64" | base64 -d > /app/data/personal/phan_minh_hoang.json
  echo "[start] personal data restored from PERSONAL_JSON_B64"
fi

if [ ! -f /app/data/staff.json ]; then
  echo "[start] WARN: data/staff.json missing — login demo will fail"
fi

exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8080}"
