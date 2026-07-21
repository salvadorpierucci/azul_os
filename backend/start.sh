#!/usr/bin/env bash
set -e

echo "=== Azul OS: Iniciando ==="

# Paths
SECRET_DB="/opt/render/project/src/azul_os.db.gz"
TARGET_DB="/opt/render/project/src/data/azul_os.db"

# Verificar si existe el secret file
if [ -f "$SECRET_DB" ]; then
  echo "Secret DB encontrado en $SECRET_DB"
  if [ ! -f "$TARGET_DB" ]; then
    echo "Restaurando base de datos desde secret file..."
    mkdir -p /opt/render/project/src/data
    gunzip -c "$SECRET_DB" > "$TARGET_DB"
    echo "✓ DB restaurada en $TARGET_DB"
    ls -lh "$TARGET_DB"
  else
    echo "La DB ya existe, saltando restauración"
  fi
else
  echo "⚠ No se encontró secret file en $SECRET_DB"
  echo "Archivos en /opt/render/project/src:"
  ls -la /opt/render/project/src/ 2>/dev/null || echo "No se pudo listar"
fi

echo "=== Iniciando uvicorn ==="
cd "$(dirname "$0")"
uvicorn app.main:app --host 0.0.0.0 --port $PORT