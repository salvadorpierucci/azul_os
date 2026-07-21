#!/usr/bin/env bash
# Backup automático de Azul OS
# Se ejecuta diariamente a las 3 AM

set -e

PROJECT_DIR="/home/sathel/proyectos/azul-os"
BACKUP_DIR="/home/sathel/backups/azul-os"
DATE=$(date +%Y%m%d_%H%M%S)

# Crear directorio de backups si no existe
mkdir -p "$BACKUP_DIR"

# Copiar la DB
cp "$PROJECT_DIR/data/azul_os.db" "$BACKUP_DIR/azul_os_$DATE.db"

# Comprimir
gzip "$BACKUP_DIR/azul_os_$DATE.db"

# Mantener solo los últimos 7 backups
ls -t "$BACKUP_DIR"/azul_os_*.db.gz | tail -n +8 | xargs -r rm

echo "Backup creado: $BACKUP_DIR/azul_os_$DATE.db.gz"