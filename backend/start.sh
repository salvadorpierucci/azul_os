#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

SECRET_DB="/opt/render/project/src/.render/SECRET_FILES/azul_os.db.gz"
TARGET_DB="/opt/render/project/src/data/azul_os.db"

if [ -f "$SECRET_DB" ] && [ ! -f "$TARGET_DB" ]; then
  echo "Restaurando base de datos desde secret file..."
  mkdir -p /opt/render/project/src/data
  gunzip -c "$SECRET_DB" > "$TARGET_DB"
  echo "DB restaurada exitosamente"
fi

uvicorn app.main:app --host 0.0.0.0 --port $PORT