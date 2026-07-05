#!/usr/bin/env bash
#
# Azul OS — Restaurar base de datos desde un backup
#
# Uso:
#   ./restore_db.sh                              (lista backups y pregunta)
#   ./restore_db.sh daily/azul_os_20250704.db.gz  (restaura backup especifico)
#   ./restore_db.sh latest                        (restaura el mas reciente)
#
# QUE HACE:
#   1. Detiene el backend (si esta corriendo)
#   2. Hace backup de la DB actual como .pre-restore
#   3. Descomprime el backup elegido
#   4. Verifica integridad
#   5. Reemplaza la DB
#   6. Avisa reiniciar el backend
#

set -euo pipefail

PROJECT_ROOT="/home/sathel/proyectos/azul-os"
DB_PATH="$PROJECT_ROOT/data/azul_os.db"
BACKUP_DIR="$PROJECT_ROOT/backups"
LOG_FILE="$BACKUP_DIR/restore.log"

mkdir -p "$BACKUP_DIR"
touch "$LOG_FILE"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"; }
die() { log "ERROR: $*"; exit 1; }

# ─── Seleccionar backup ───
if [ $# -eq 0 ]; then
    echo "Backups disponibles:"
    echo ""
    echo "  DIARIOS:"
    ls -1t "$BACKUP_DIR/daily"/azul_os_*.db.gz 2>/dev/null | head -10 | while read -r f; do
        echo "    daily/$(basename "$f")  ($(du -h "$f" | cut -f1), $(date -r "$f" '+%d/%m %H:%M'))"
    done || echo "    (sin backups)"
    echo ""
    echo "  SEMANALES:"
    ls -1t "$BACKUP_DIR/weekly"/azul_os_*.db.gz 2>/dev/null | while read -r f; do
        echo "    weekly/$(basename "$f")  ($(du -h "$f" | cut -f1), $(date -r "$f" '+%d/%m %H:%M'))"
    done || echo "    (sin backups)"
    echo ""
    echo "  MENSUALES:"
    ls -1t "$BACKUP_DIR/monthly"/azul_os_*.db.gz 2>/dev/null | while read -r f; do
        echo "    monthly/$(basename "$f")  ($(du -h "$f" | cut -f1), $(date -r "$f" '+%d/%m %H:%M'))"
    done || echo "    (sin backups)"
    echo ""
    echo "Uso:"
    echo "  $0 daily/azul_os_20250704_030001.db.gz    (restaurar backup especifico)"
    echo "  $0 latest                                  (restaurar el mas reciente)"
    echo "  $0 list                                    (ver lista)"
    exit 0
fi

SELECTION="$1"

if [ "$SELECTION" = "list" ]; then
    exec "$0"
fi

# Resolver path del backup
if [ "$SELECTION" = "latest" ]; then
    BACKUP_FILE=$(ls -1t "$BACKUP_DIR/daily"/azul_os_*.db.gz 2>/dev/null | head -1)
    if [ -z "$BACKUP_FILE" ]; then
        die "No hay backups disponibles"
    fi
elif [[ "$SELECTION" == */* ]]; then
    # Path relative: daily/archivo.db.gz
    BACKUP_FILE="$BACKUP_DIR/$SELECTION"
else
    # Buscar por nombre en todos los subdirs
    BACKUP_FILE=$(find "$BACKUP_DIR" -name "$SELECTION" -type f | head -1)
fi

if [ -z "$BACKUP_FILE" ] || [ ! -f "$BACKUP_FILE" ]; then
    die "Backup no encontrado: $SELECTION"
fi

log "=== Restauracion ==="
log "Backup seleccionado: $BACKUP_FILE ($(du -h "$BACKUP_FILE" | cut -f1))"

# ─── Paso 1: Detener el backend ───
log "Deteniendo backend..."
PID=""
if [ -f /tmp/azul_backend.pid ]; then
    PID=$(cat /tmp/azul_backend.pid)
fi
if [ -z "$PID" ]; then
    PID=$(pgrep -f 'uvicorn app.main' || true)
fi
if [ -n "$PID" ]; then
    log "  Matando proceso $PID"
    kill "$PID" 2>/dev/null || true
    sleep 2
    # Verificar que murio
    if kill -0 "$PID" 2>/dev/null; then
        log "  Proceso no cerro, forzando..."
        kill -9 "$PID" 2>/dev/null || true
        sleep 1
    fi
else
    log "  Backend no estaba corriendo"
fi

# ─── Paso 2: Backup de la DB actual (pre-restore) ───
if [ -f "$DB_PATH" ]; then
    PRE_RESTORE="$DB_PATH.pre-restore.$(date +%Y%m%d_%H%M%S)"
    log "Respaldando DB actual a: $PRE_RESTORE"
    cp "$DB_PATH" "$PRE_RESTORE"
fi

# ─── Paso 3: Descomprimir y restaurar ───
TEMP_DB=$(mktemp /tmp/azul_restore_XXXXXX.db)
log "Descomprimiendo backup..."
gunzip -c "$BACKUP_FILE" > "$TEMP_DB"

log "Verificando integridad del backup..."
INTEGRITY=$(sqlite3 "$TEMP_DB" "PRAGMA integrity_check;" 2>&1)
if [ "$INTEGRITY" != "ok" ]; then
    rm -f "$TEMP_DB"
    die "Backup corrupto (integrity_check: $INTEGRITY)"
fi
log "Integridad OK"

log "Reemplazando DB..."
mv "$TEMP_DB" "$DB_PATH"
log "DB restaurada: $DB_PATH ($(du -h "$DB_PATH" | cut -f1))"

# ─── Paso 4: Avisar reiniciar ───
log "=== Restauracion completada ==="
echo ""
echo "DB restaurada correctamente desde: $BACKUP_FILE"
echo ""
echo "Para reiniciar el backend ejecuta:"
echo "  ~/scripts/start_all.sh"
echo ""
echo "Si algo salio mal, la DB anterior esta en:"
echo "  $(ls -1t "${DB_PATH}".pre-restore.* 2>/dev/null | head -1)"
