#!/bin/bash
# ============================================
# Azul OS - Script de inicio
# ============================================
# Detecta automáticamente la ruta del proyecto.
# Funciona en cualquier máquina (no usa rutas hardcodeadas).
# ============================================

set -e

# Autodetectar ruta del proyecto (directorio donde está este script)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"

echo "=== Azul OS - Iniciando ==="
echo ""

# 1. Cargar variables de entorno desde .env si existe
ENV_FILE="$BACKEND_DIR/.env"
if [ -f "$ENV_FILE" ]; then
    echo "📂 Cargando .env..."
    set -a
    source "$ENV_FILE"
    set +a
else
    echo "⚠️  No se encontró .env en $ENV_FILE"
    echo "   Copia .env.example a .env y completa tus credenciales:"
    echo "   cp $BACKEND_DIR/.env.example $ENV_FILE"
    echo ""
fi

# 2. Verificar Twilio configurado (opcional, la app funciona sin WhatsApp)
if [ -z "$TWILIO_ACCOUNT_SID" ]; then
    echo "⚠️  TWILIO_ACCOUNT_SID no configurado en .env"
    echo "   La app funcionará sin WhatsApp. Configúralo más tarde."
    echo ""
else
    echo "✅ Twilio configurado"
    echo "   Account: $TWILIO_ACCOUNT_SID"
    echo ""
fi

# 3. Crear entorno virtual si no existe
VENV_DIR="$SCRIPT_DIR/venv"
if [ ! -d "$VENV_DIR" ]; then
    echo "🐍 Creando entorno virtual..."
    python3 -m venv "$VENV_DIR"
    echo "📦 Instalando dependencias..."
    "$VENV_DIR/bin/pip" install -r "$BACKEND_DIR/requirements.txt"
    echo ""
fi

# 4. Iniciar backend
PORT="${PORT:-8000}"

# Verificar si ya está corriendo
if lsof -ti :$PORT > /dev/null 2>&1; then
    echo "✅ Backend ya está corriendo en puerto $PORT"
else
    echo "🚀 Iniciando backend en puerto $PORT..."
    cd "$BACKEND_DIR"
    "$VENV_DIR/bin/python" -m uvicorn app.main:app --host 0.0.0.0 --port "$PORT" &
    BACKEND_PID=$!
    echo $BACKEND_PID > /tmp/azul_backend.pid
    sleep 3
    
    if curl -s "http://localhost:$PORT/" > /dev/null 2>&1; then
        echo "✅ Backend corriendo (PID: $BACKEND_PID)"
    else
        echo "⏳ Esperando..."
        sleep 2
    fi
fi

echo ""
echo "=== Azul OS Listo ==="
echo ""
echo "Acceso:"
echo "  • Local:    http://localhost:$PORT"
echo "  • Red LAN: http://$(hostname -I | awk '{print $1}'):$PORT"
echo "  • Api docs: http://localhost:$PORT/docs"
echo ""
echo "Para detener:"
echo "  kill \$(cat /tmp/azul_backend.pid 2>/dev/null)"
echo "  o: pkill -f 'uvicorn app.main'"
