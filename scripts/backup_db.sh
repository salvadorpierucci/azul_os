#!/usr/bin/env bash
#
# Azul OS — Backup automatico de la base de datos SQLite
#
# Que hace:
#   1. Usa sqlite3 .backup (copia segura en caliente, no corrompe la DB)
#   2. Comprime con gzip
#   3. Rota: mantiene 7 diarios, 4 semanales, 3 mensuales
#   4. Loggea todo en backup.log
#   5. Verifica integridad del backup (sqlite3 integrity_check)
#
# Uso:
#   ./backup_db.sh                (usa paths por defecto)
#   ./backup_db.sh /path/to/db    (DB custom)
#
# Cron recomendado: todos los dias a las 03:00
#   0 3 * * * /home/sathel/proyectos/azul-os/scripts/backup_db.sh >> /dev/null 2>&1
#

set -euo pipefail

# ─── Configuracion ───
PROJECT_ROOT="/home/sathel/proyectos/azul-os"
DB_PATH="${1:-$PROJECT_ROOT/data/azul_os.db}"
BACKUP_DIR="$PROJECT_ROOT/backups"
LOG_FILE="$BACKUP_DIR/backup.log"

# Estructura: backups/daily/, backups/weekly/, backups/monthly/
DAILY_DIR="$BACKUP_DIR/daily"
WEEKLY_DIR="$BACKUP_DIR/weekly"
MONTHLY_DIR="$BACKUP_DIR/monthly"

DAILY_KEEP=7    # mantener 7 backups diarios
WEEKLY_KEEP=4   # mantener 4 backups semanales
MONTHLY_KEEP=3  # mantener 3 backups mensuales

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
DATE_TODAY=$(date +"%Y-%m-%d")
DOW=$(date +%u)   # dia de la semana: 1=Lun, 7=Dom
DOM=$(date +%-d)  # dia del mes

# ─── Funciones ───
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

die() {
    log "ERROR: $*"
    exit 1
}

# ─── Init ───
mkdir -p "$DAILY_DIR" "$WEEKLY_DIR" "$MONTHLY_DIR"
touch "$LOG_FILE"

log "=== Iniciando backup ==="

# Verificar que la DB existe
if [ ! -f "$DB_PATH" ]; then
    die "DB no encontrada: $DB_PATH"
fi

# Verificar que sqlite3 este instalado
if ! command -v sqlite3 &>/dev/null; then
    die "sqlite3 no esta instalado. Ejecutar: sudo apt install sqlite3"
fi

# ─── Paso 1: Backup seguro en caliente ───
# sqlite3 .backup hace una copia consistente sin bloquear la DB
# Es seguro incluso si la app esta escribiendo
DAILY_FILE="$DAILY_DIR/azul_os_${TIMESTAMP}.db"

log "Copiando DB (sqlite3 .backup)..."
sqlite3 "$DB_PATH" ".backup '$DAILY_FILE'" || die "Fallo el backup de sqlite3"
log "Backup copiado a: $DAILY_FILE"

# ─── Paso 2: Verificar integridad ───
log "Verificando integridad..."
INTEGRITY=$(sqlite3 "$DAILY_FILE" "PRAGMA integrity_check;" 2>&1)
if [ "$INTEGRITY" != "ok" ]; then
    die "Backup corrupto (integrity_check: $INTEGRITY)"
fi
log "Integridad OK"

# ─── Paso 3: Comprimir ───
log "Comprimiendo..."
gzip -f "$DAILY_FILE"
DAILY_GZ="${DAILY_FILE}.gz"
log "Comprimido: $DAILY_GZ ($(du -h "$DAILY_GZ" | cut -f1))"

# ─── Paso 4: Rotacion ───
# Rotar diarios: mantener solo los ultimos DAILY_KEEP
log "Rotando backups diarios (mantener $DAILY_KEEP)..."
ls -1t "$DAILY_DIR"/azul_os_*.db.gz 2>/dev/null | tail -n +$((DAILY_KEEP + 1)) | while read -r old; do
    log "  Eliminando: $(basename "$old")"
    rm -f "$old"
done

# Backup semanal: los Domingos (DOW=7), copiar el backup diario a weekly/
if [ "$DOW" = "7" ]; then
    log "Es Domingo — creando backup semanal..."
    WEEKLY_FILE="$WEEKLY_DIR/azul_os_${TIMESTAMP}.db.gz"
    cp "$DAILY_GZ" "$WEEKLY_FILE"
    log "Semanal: $WEEKLY_FILE"

    # Rotar semanales
    log "Rotando backups semanales (mantener $WEEKLY_KEEP)..."
    ls -1t "$WEEKLY_DIR"/azul_os_*.db.gz 2>/dev/null | tail -n +$((WEEKLY_KEEP + 1)) | while read -r old; do
        log "  Eliminando: $(basename "$old")"
        rm -f "$old"
    done
fi

# Backup mensual: el dia 1 de cada mes, copiar a monthly/
if [ "$DOM" = "1" ]; then
    log "Es dia 1 — creando backup mensual..."
    MONTHLY_FILE="$MONTHLY_DIR/azul_os_${TIMESTAMP}.db.gz"
    cp "$DAILY_GZ" "$MONTHLY_FILE"
    log "Mensual: $MONTHLY_FILE"

    # Rotar mensuales
    log "Rotando backups mensuales (mantener $MONTHLY_KEEP)..."
    ls -1t "$MONTHLY_DIR"/azul_os_*.db.gz 2>/dev/null | tail -n +$((MONTHLY_KEEP + 1)) | while read -r old; do
        log "  Eliminando: $(basename "$old")"
        rm -f "$old"
    done
fi

# ─── Paso 5: Resumen ───
DAILY_COUNT=$(ls -1 "$DAILY_DIR"/azul_os_*.db.gz 2>/dev/null | wc -l)
WEEKLY_COUNT=$(ls -1 "$WEEKLY_DIR"/azul_os_*.db.gz 2>/dev/null | wc -l)
MONTHLY_COUNT=$(ls -1 "$MONTHLY_DIR"/azul_os_*.db.gz 2>/dev/null | wc -l)
DB_SIZE=$(du -h "$DB_PATH" | cut -f1)

log "=== Backup completado ==="
log "  DB original: $DB_SIZE ($DB_PATH)"
log "  Diarios: $DAILY_COUNT archivos"
log "  Semanales: $WEEKLY_COUNT archivos"
log "  Mensuales: $MONTHLY_COUNT archivos"
log "  Total backups: $(du -sh "$BACKUP_DIR" | cut -f1)"
