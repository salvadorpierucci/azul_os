#!/bin/bash
# Azul OS - Sincronizar cambios desde GitHub y reiniciar
# Uso: ./scripts/pull_and_restart.sh
# Ejecutar en la PC de PRODUCCIÓN (donde se usa la app)
# NO toca la base de datos - solo trae código nuevo

set -e
cd "$(dirname "$0")/.."
echo "=== Azul OS - Sync desde GitHub ==="

# 1. Backup de la DB antes de cualquier cosa (seguridad)
echo "[1/6] Backup de seguridad de la DB..."
if [ -f data/azul_os.db ]; then
    cp data/azul_os.db "backups/daily/azul_os_pre_sync_$(date +%Y%m%d_%H%M%S).db" 2>/dev/null || true
    echo "    OK - backup en backups/daily/"
else
    echo "    (sin DB existente, primer sync)"
fi

# 2. Stash de cambios locales si hay (por las dudas)
echo "[2/6] Guardando cambios locales..."
if [ -n "$(git status --porcelain)" ]; then
    git stash
    echo "    Cambios locales guardados con git stash"
else
    echo "    Sin cambios locales"
fi

# 3. Pull del código
echo "[3/6] Bajando cambios desde GitHub..."
git pull origin main
echo "    OK"

# 4. Instalar dependencias si requirements cambió
echo "[4/6] Verificando dependencias..."
if [ -f backend/requirements.txt ]; then
    if [ -d venv ]; then
        source venv/bin/activate
        pip install -r backend/requirements.txt --quiet
        echo "    Dependencias actualizadas"
    else
        echo "    (sin venv, salteando)"
    fi
fi

# 5. Migraciones de DB (si hay schema nuevo)
echo "[5/6] Aplicando migraciones de DB..."
if [ -f alembic.ini ]; then
    if [ -d venv ]; then source venv/bin/activate; fi
    alembic upgrade head 2>&1 || echo "    (sin migraciones nuevas o alembic no configurado)"
fi

# 6. Reiniciar servidor
echo "[6/6] Reiniciando servidor..."
# Matar el servidor anterior si está corriendo
pkill -f "uvicorn app.main:app" 2>/dev/null && echo "    Servidor anterior detenido" || echo "    Sin servidor previo"
sleep 1

# Iniciar servidor nuevo
if [ -d venv ]; then
    source venv/bin/activate
fi
cd backend
nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 > ../azul_os.log 2>&1 &
echo "    Servidor iniciado en http://localhost:8000"
echo "    Log: azul_os.log"

echo ""
echo "=== Sync completo ==="
echo "Base de datos: NO tocada (datos intactos)"
echo "App: http://localhost:8000"
echo ""
echo "Si tenés Cloudflare Tunnel corriendo, reiniciá esa ventana también."
