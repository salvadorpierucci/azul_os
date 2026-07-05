# Azul OS — Sistema de Gestión de Eventos

Sistema de gestión para **Azul Livings** — alquiler de mobiliario para eventos.

## Requisitos

- **Python 3.10+** (probado con 3.12)
- **Linux, macOS o Windows** (con WSL o Git Bash recomendado en Windows)
- Conexión a internet (solo para Twilio WhatsApp y Tailwind CDN)

## Instalación

### 1. Descargar el proyecto

```bash
# Opción A: Git clone (si usas repo)
git clone <url-del-repo> azul-os
cd azul-os

# Opción B: Copiar carpeta manualmente
# Copia toda la carpeta azul-os/ a la nueva máquina
cd azul-os
```

### 2. Crear entorno virtual e instalar dependencias

```bash
python3 -m venv venv
source venv/bin/activate    # Linux/macOS
# venv\Scripts\activate     # Windows
pip install -r backend/requirements.txt
```

### 3. Configurar credenciales

```bash
cp backend/.env.example backend/.env
# Edita backend/.env con tus credenciales de Twilio
```

### 4. Iniciar el servidor

```bash
./start_all.sh
# o manualmente:
cd backend
source ../venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 5. Abrir en el navegador

- **Local**: http://localhost:8000
- **Red LAN**: http://<IP-DEL-SERVIDOR>:8000

## Acceso desde otras computadoras (Windows, Mac, etc.)

1. **En la máquina servidor** (donde corre Azul OS):
   - Verificar la IP local: `hostname -I` (Linux) o `ipconfig` (Windows)
   - Asegurarse que el firewall permita conexiones al puerto 8000

2. **En las máquinas cliente** (Windows, Mac, etc.):
   - Abrir el navegador
   - Ir a `http://<IP-DEL-SERVIDOR>:8000`
   - Ejemplo: `http://192.168.1.100:8000`

3. **Firewall** (si no conecta):
   ```bash
   # Linux (ufw)
   sudo ufw allow 8000/tcp

   # Windows
   netsh advfirewall firewall add rule name="Azul OS" dir=in action=allow protocol=tcp localport=8000
   ```

## Configurar WhatsApp (Twilio)

1. Crear cuenta en https://www.twilio.com/console
2. Activar WhatsApp Sandbox (gratis) o comprar un número
3. Copiar `Account SID` y `Auth Token` a `backend/.env`
4. Verificar números de destino si usás trial

## Estructura del proyecto

```
azul-os/
├── start_all.sh              # Script de inicio (auto-detecta rutas)
├── backend/
│   ├── .env                  # Tus credenciales (NO se comparte)
│   ├── .env.example          # Template de credenciales
│   ├── requirements.txt      # Dependencias Python
│   └── app/
│       ├── main.py           # FastAPI app
│       ├── database.py       # SQLite setup
│       ├── models.py          # Modelos de datos
│       ├── schemas.py        # Pydantic schemas
│       ├── parser.py          # Parser de mensajes WhatsApp
│       └── routers/
│           ├── mobiliario.py
│           ├── eventos.py
│           ├── finanzas.py
│           ├── presupuestos.py
│           ├── whatsapp_twilio.py
│           └── debug.py
├── frontend/
│   ├── index.html            # SPA
│   ├── css/app.css
│   └── js/
│       ├── api.js            # API client (URL dinámica)
│       └── app.js            # Lógica del frontend
├── data/                     # SQLite DB (se crea automáticamente)
└── uploads/                  # Fotos de mobiliario
```

## Datos técnicos

- **Base de datos**: SQLite (se crea automáticamente en `data/azul_os.db`)
- **Backend**: FastAPI + uvicorn
- **Frontend**: HTML/CSS/JS vanilla + Tailwind CSS (CDN)
- **WhatsApp**: Twilio WhatsApp API
- **PDF**: ReportLab (presupuestos en PDF)

## Acceso desde Internet (fuera de casa)

### Opción rapida: TryCloudflare (gratis, sin dominio)

```bash
./start_remote.sh
```

Esto levanta el backend + un tunel de Cloudflare y te da una URL publica como:
  https://random-words.trycloudflare.com

Compartila con quien quieras que acceda. La URL cambia cada vez que reinicias el script.

**Limitaciones de TryCloudflare**:
- La URL es random y cambia al reiniciar
- No hay garantia de uptime (es para pruebas/uso casual)
- Si necesitas URL fija (ej: azul.tudominio.com), compra un dominio (~$10/año) y usa Cloudflare Tunnel con cuenta

### Opción fija: Cloudflare Tunnel con dominio

1. Comprar un dominio (ej: en Namecheap, Google Domains)
2. Crear cuenta gratis en Cloudflare y migrar el dominio alli
3. Crear un named tunnel:
   ```bash
   cloudflared tunnel login
   cloudflared tunnel create azul-os
   cloudflared tunnel route dns azul-os azul.tudominio.com
   ```
4. Configurar ~/.cloudflared/config.yml:
   ```yaml
   tunnel: <tunnel-id>
   credentials-file: /home/usuario/.cloudflared/<tunnel-id>.json
   ingress:
     - hostname: azul.tudominio.com
       service: http://localhost:8000
     - service: http_status:404
   ```
5. Iniciar:
   ```bash
   cloudflared tunnel run azul-os
   ```

## Solución de problemas

**No conecta desde otra PC**:
- Verificar que el servidor escucha en 0.0.0.0 (no 127.0.0.1)
- Verificar firewall del servidor permita puerto 8000
- Verificar que ambas PCs estén en la misma red (o VPN)

**La DB se perdió**:
- Se crea automáticamente al iniciar. Los datos previos están en `data/azul_os.db`
- Diagnóstico: `curl http://localhost:8000/api/debug/db-info`

**WhatsApp no envía**:
- Verificar credenciales en `.env`
- Si usás trial de Twilio, solo envía a números verificados
- Log de Twilio: https://www.twilio.com/console/logs

**No carga los estilos (Tailwind)**:
- Tailwind se carga via CDN, necesita internet
- Si no hay internet, descargar tailwind.css localmente
