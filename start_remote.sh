#!/bin/bash
# ============================================
# Azul OS - Inicio con acceso remoto via TryCloudflare
# ============================================
# Levanta el backend + tunel de Cloudflare en un solo comando.
# Cualquier persona puede acceder desde internet via la URL que muestra.
# ============================================

# set -e desactivado: rompe el while-read del tunel cloudflared por heredar ERR traps
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== Azul OS - Iniciando con accesso remoto ==="
echo ""

# 1. Iniciar backend (reusa start_all.sh)
if lsof -ti :8000 > /dev/null 2>&1; then
    echo "✅ Backend ya corriendo en puerto 8000"
else
    echo "🚀 Iniciando backend..."
    bash "$SCRIPT_DIR/start_all.sh" > /dev/null 2>&1 &
    sleep 5
    if lsof -ti :8000 > /dev/null 2>&1; then
        echo "✅ Backend corriendo"
    else
        echo "❌ No se pudo iniciar el backend"
        exit 1
    fi
fi

echo ""

# 2. Iniciar tunel TryCloudflare
echo "🌐 Iniciando tunel Cloudflare..."

# Limpiar PID anterior si existe
TUNNEL_PID_FILE="/tmp/azul_cloudflared.pid"
if [ -f "$TUNNEL_PID_FILE" ]; then
    OLD_PID=$(cat "$TUNNEL_PID_FILE")
    if kill -0 "$OLD_PID" 2>/dev/null; then
        echo "✅ Tunel ya corriendo (PID: $OLD_PID)"
        echo ""
        echo "=== Azul OS Listo ==="
        echo ""
        echo "Busca la URL en los logs del tunel, o en:"
        echo "  ~/scripts/start_remote.sh  (re-ejecutar muestra la URL)"
        exit 0
    fi
fi

# Levantar tunel y capturar la URL
cloudflared tunnel --url http://localhost:8000 2>&1 | while IFS= read -r line; do
    echo "$line"
    # Extraer URL del output
    if echo "$line" | grep -q "trycloudflare.com"; then
        URL=$(echo "$line" | grep -oP 'https://[a-z0-9-]+\.trycloudflare\.com')
        if [ -n "$URL" ]; then
            echo "$URL" > /tmp/azul_tunnel_url.txt
            echo ""
            echo "═══════════════════════════════════════════════"
            echo "  ✅ AZUL OS ACCESIBLE DESDE INTERNET"
            echo "═══════════════════════════════════════════════"
            echo ""
            echo "  URL pública: $URL"
            echo ""
            echo "  Local: http://localhost:8000"
            echo "  Red LAN: http://$(hostname -I | awk '{print $1}'):8000"
            echo ""
            echo "  Comparte esta URL con quien quieras que acceda."
            echo "  (La URL cambia si reinicias este script)"
            echo "═══════════════════════════════════════════════"
        fi
    fi
done &
TUNNEL_PID=$!
echo $TUNNEL_PID > "$TUNNEL_PID_FILE"

# Esperar a que el tunel asigne la URL
sleep 8

# Mostrar URL si ya está disponible
if [ -f /tmp/azul_tunnel_url.txt ]; then
    cat /tmp/azul_tunnel_url.txt
fi
