#!/usr/bin/env python3
"""
Azul OS — Backup automatico de la base de datos SQLite (cross-platform)

Hace:
  1. Copia en caliente segura (sqlite3 .backup) — no corrompe si la app esta escribiendo
  2. Compresion con gzip
  3. Verifica integridad del backup (PRAGMA integrity_check)
  4. Rotacion: 7 diarios, 4 semanales, 3 mensuales
  5. Loggea todo en backups/backup.log

Funciona en Windows, Linux y macOS. Solo necesita Python stdlib.

Uso:
  python scripts/backup_db.py                    (paths por defecto)
  python scripts/backup_db.py /ruta/a/la.db      (DB custom)
"""

import os
import sys
import sqlite3
import gzip
import shutil
import datetime
from glob import glob

# ─── Config ────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)

DB_PATH = sys.argv[1] if len(sys.argv) > 1 else os.path.join(PROJECT_ROOT, "data", "azul_os.db")
BACKUP_DIR = os.path.join(PROJECT_ROOT, "backups")
LOG_FILE = os.path.join(BACKUP_DIR, "backup.log")

DAILY_DIR = os.path.join(BACKUP_DIR, "daily")
WEEKLY_DIR = os.path.join(BACKUP_DIR, "weekly")
MONTHLY_DIR = os.path.join(BACKUP_DIR, "monthly")

DAILY_KEEP = 7
WEEKLY_KEEP = 4
MONTHLY_KEEP = 3


def log(msg: str) -> None:
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass


def die(msg: str) -> None:
    log(f"ERROR: {msg}")
    sys.exit(1)


def rotate_dir(directory: str, keep: int, pattern: str) -> None:
    """Mantiene solo los ultimos `keep` archivos en `directory`."""
    files = sorted(glob(os.path.join(directory, pattern)), key=os.path.getmtime, reverse=True)
    for old in files[keep:]:
        log(f"  Eliminando: {os.path.basename(old)}")
        os.remove(old)


# ─── Main ───────────────────────────────────────────────────────
os.makedirs(DAILY_DIR, exist_ok=True)
os.makedirs(WEEKLY_DIR, exist_ok=True)
os.makedirs(MONTHLY_DIR, exist_ok=True)

now = datetime.datetime.now()
timestamp = now.strftime("%Y%m%d_%H%M%S")
dow = now.isoweekday()   # 1=Lun ... 7=Dom
dom = now.day            # dia del mes

log("=== Iniciando backup ===")

if not os.path.isfile(DB_PATH):
    die(f"DB no encontrada: {DB_PATH}")

# 1. Copia en caliente (sqlite3 .backup)
daily_file = os.path.join(DAILY_DIR, f"azul_os_{timestamp}.db")
log("Copiando DB (sqlite3 .backup en caliente)...")

try:
    src = sqlite3.connect(DB_PATH)
    dst = sqlite3.connect(daily_file)
    src.backup(dst)
    dst.close()
    src.close()
except Exception as e:
    die(f"Fallo backup sqlite3: {e}")

log(f"Backup copiado a: {daily_file}")

# 2. Verificar integridad
log("Verificando integridad...")
try:
    conn = sqlite3.connect(daily_file)
    cur = conn.execute("PRAGMA integrity_check;")
    result = cur.fetchone()[0]
    conn.close()
    if result != "ok":
        die(f"Backup corrupto (integrity_check: {result})")
except Exception as e:
    die(f"Error verificando integridad: {e}")
log("Integridad OK")

# 3. Comprimir
log("Comprimiendo...")
daily_gz = daily_file + ".gz"
try:
    with open(daily_file, "rb") as f_in:
        with gzip.open(daily_gz, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)
    os.remove(daily_file)  # borrar version sin comprimir
    size = os.path.getsize(daily_gz)
    if size < 1024:
        log(f"Comprimido: {daily_gz} ({size} bytes)")
    elif size < 1024 * 1024:
        log(f"Comprimido: {daily_gz} ({size / 1024:.1f} KB)")
    else:
        log(f"Comprimido: {daily_gz} ({size / 1024 / 1024:.1f} MB)")
except Exception as e:
    log(f"ADVERTENCIA: No se pudo comprimir ({e}) — guardando sin comprimir")
    daily_gz = daily_file

# 4. Rotacion diaria
log(f"Rotando backups diarios (mantener {DAILY_KEEP})...")
rotate_dir(DAILY_DIR, DAILY_KEEP, "azul_os_*.db.gz")

# 5. Backup semanal (Domingos)
if dow == 7:
    log("Es Domingo — creando backup semanal...")
    weekly_file = os.path.join(WEEKLY_DIR, f"azul_os_{timestamp}.db.gz")
    shutil.copy2(daily_gz, weekly_file)
    log(f"Semanal: {weekly_file}")
    rotate_dir(WEEKLY_DIR, WEEKLY_KEEP, "azul_os_*.db.gz")

# 6. Backup mensual (dia 1)
if dom == 1:
    log("Es dia 1 — creando backup mensual...")
    monthly_file = os.path.join(MONTHLY_DIR, f"azul_os_{timestamp}.db.gz")
    shutil.copy2(daily_gz, monthly_file)
    log(f"Mensual: {monthly_file}")
    rotate_dir(MONTHLY_DIR, MONTHLY_KEEP, "azul_os_*.db.gz")

# 7. Resumen
daily_count = len(glob(os.path.join(DAILY_DIR, "azul_os_*.db.gz")))
weekly_count = len(glob(os.path.join(WEEKLY_DIR, "azul_os_*.db.gz")))
monthly_count = len(glob(os.path.join(MONTHLY_DIR, "azul_os_*.db.gz")))
db_size = os.path.getsize(DB_PATH) if os.path.isfile(DB_PATH) else 0
backup_total = sum(d.stat().st_size for d in (
    os.scandir(BACKUP_DIR)
) if d.is_file() and d.name.endswith(".db.gz"))

log("=== Backup completado ===")
log(f"  DB original: {db_size / 1024:.1f} KB ({DB_PATH})")
log(f"  Diarios: {daily_count} archivos")
log(f"  Semanales: {weekly_count} archivos")
log(f"  Mensuales: {monthly_count} archivos")
log(f"  Total backups: {backup_total / 1024:.1f} KB")