# PLAN: Nuevo Instalador Azul OS para Windows 11

**Objetivo:** Generar un ZIP auto-extraíble que, al descomprimirse y ejecutar instalar.bat en una Windows 11 limpia, deje Azul OS funcionando en localhost:8000 con base de datos persistente, backups automáticos, y todo configurable desde la propia aplicación.

---

## Estado actual vs. instalador anterior

Ya existe un instalador Windows previo (`~/Descargas/azul-os-instalador-windows.zip`) con 66 archivos. Funciona, pero tiene problemas que este nuevo instalador debe resolver:

1. **El repo actual cargaba `.env` desde `~/.config/azul-os/.env`** (fuera del repo) — el instalador anterior lo ponía en `backend/.env`. Hay que decidir y unificar.
2. **El backup.bat anterior usaba `copy` directo** — no usa `sqlite3 .backup` (copia en caliente segura). Si la app está escribiendo, el backup puede corromperse.
3. **El backup.bat anterior no comprime** — el script .sh sí hace gzip + verificación de integridad + rotación diaria/semanal/mensual. El .bat solo rota diarios.
4. **No incluye la DB actual** — el instalador anterior venía con `data/` vacío. La DB se inicializa desde cero con seed data, sin los datos reales del negocio.
5. **No hay forma de importar la DB real** — el usuario tiene datos en `data/azul_os.db` (147KB) que probablemente quiera llevar a Windows.
6. **El instalador anterior instalaba cloudflared** — para acceso desde internet. El usuario esta vez pidió solo localhost.
7. **El .bat del launcher anterior usaba `python -m uvicorn` directo** — si el server crashea, la ventana se cierra y no se ve el error.
8. **No incluía `alembic` ni las migraciones** — el repo actual sí las tiene.

---

## Estructura del nuevo ZIP

```
azul-os-windows/
├── instalar.bat                 # Instalador principal (doble-click)
├── iniciar.bat                  # Launcher (doble-click para usar después)
├── LEEME.txt                    # Instrucciones claras para el usuario
├── backend/
│   ├── app/                     # Código Python (idéntico al repo)
│   │   ├── __init__.py
│   │   ├── main.py              # MODIFICADO: .env en backend/ (no ~/.config)
│   │   ├── database.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── parser.py
│   │   ├── pdf_gen.py
│   │   ├── auth.py
│   │   └── routers/
│   │       ├── __init__.py
│   │       ├── mobiliario.py
│   │       ├── eventos.py
│   │       ├── finanzas.py
│   │       ├── presupuestos.py
│   │       ├── debug.py
│   │       └── whatsapp_twilio.py
│   ├── requirements.txt
│   ├── .env.example
│   └── alembic/                 # Migraciones (por si futuras versiones)
│       ├── env.py
│       ├── script.py.mako
│       └── versions/
│           └── d2aa9cf5e15d_initial_schema.py
├── frontend/
│   ├── index.html
│   ├── css/app.css
│   └── js/
│       ├── api.js
│       ├── app.js
│       ├── calendario.js
│       ├── clientes.js
│       ├── dashboard.js
│       ├── eventos.js
│       ├── finanzas.js
│       ├── mobiliario.js
│       ├── presupuestos.js
│       ├── state.js
│       ├── ui.js
│       └── whatsapp.js
├── tests/
│   └── test_azul_os.py
├── scripts/
│   ├── backup_db.bat            # NUEVO: backup con copia segura
│   ├── backup_db.py             # NUEVO: backup en Python (sqlite3 .backup + gzip)
│   ├── restore_db.bat           # Restaurar desde backup
│   └── backup_diario.py         # NUEVO: wrapper para Task Scheduler
├── data/
│   └── azul_os.db               # DB actual del negocio (opcional, ver abajo)
├── uploads/
│   └── mobiliario/              # Fotos (vacío si no hay)
└── .gitignore
```

**NOTA sobre `data/azul_os.db`:** Hay dos opciones:
- **Opción A — DB limpia:** El instalador crea la DB desde cero con seed data (zonas logísticas, config WhatsApp). El usuario arranca sin datos.
- **Opción B — DB con datos actuales:** Incluimos la DB actual (147KB) en el ZIP. El usuario tiene sus eventos, clientes, mobiliario en Windows.
- → Preguntar al usuario cuál prefiere.

---

## Pasos del instalador (instalar.bat)

### PASO 1/7: Verificar Python 3.10+
- Detectar si `python` está en PATH y es versión >= 3.10
- Si no, abrir descarga de Python 3.12 (winget o descarga manual)
- Pausar y pedir re-ejecutar después

### PASO 2/7: Entorno virtual + dependencias
- `python -m venv venv`
- `venv\Scripts\pip install -r backend\requirements.txt`
- `venv\Scripts\pip install alembic pytest openpyxl`
- Mostrar qué se instaló

### PASO 3/7: Configurar .env
- Copiar `backend\.env.example` → `backend\.env`
- Generar token aleatorio: `python -c "import secrets; print(secrets.token_hex(32))"`
- Setear `AZUL_AUTH_TOKEN=< generado >` y `AZUL_AUTH_PASSWORD=azul`
- Mostrar token y password al usuario
- Setear `AZUL_CORS_ORIGINS=` (vacío = solo localhost)

### PASO 4/7: Base de datos
- Si ya hay `data\azul_os.db` (incluida en ZIP o ya existente), NO sobrescribir
- Si no existe, crear: `python -c "from app.database import init_db; init_db()"`
- Verificar que la DB existe con `python -c "import sqlite3; ... integrity_check"`

### PASO 5/7: Backups automáticos
- Crear `scripts\backup_db.py` (backup en caliente con `sqlite3 .backup`, compression con gzip opcional, volición diaria/semanal/mensual)
- Crear `scripts\backup_db.bat` que llama al .py
- Registrar tarea programada: `schtasks /create /tn "Azul OS Backup Diario" /tr "..." /sc daily /st 03:00 /f`
- También hacer backup al iniciar (en `iniciar.bat`, antes del servidor)

### PASO 6/7: Launcher (iniciar.bat)
- Crear `iniciar.bat` en la raíz:
  1. `call venv\Scripts\activate.bat`
  2. `cd backend`  
  3. Ejecutar backup opcional antes de iniciar
  4. `python -m uvicorn app.main:app --host 0.0.0.0 --port 8000`
  5. `pause` si crashea (para ver el error)
- Abrir `http://localhost:8000` automáticamente

### PASO 7/7: Accesos directos
- Crear acceso directo en Escritorio: "Azul OS" → `iniciar.bat`
- Crear acceso directo en Menú Inicio > Programas > Azul OS
- Mostrar resumen final con password, URL, y comandos útiles

---

## Modificaciones al código fuente (backend/app/main.py)

El `main.py` actual carga `.env` desde `~/.config/azul-os/.env` (
Linux). En Windows, esa ruta es `%USERPROFILE%\.config\azul-os\.env` que no es natural. **Cambio:** hacer que cargue `backend/.env` si existe, y si no,
`~/.config/azul-os/.env` como fallback:

```python
# Cargar .env: primero backend/.env, luego ~/.config/azul-os/.env
_env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
if os.path.exists(_env_path):
    load_dotenv(_env_path)
else:
    _env_alt = os.path.expanduser("~/.config/azul-os/.env")
    if os.path.exists(_env_alt):
        load_dotenv(_env_alt)
```

Esto es lo único que cambia del código — todo lo demás del repo va idéntico.

---

## Backup automático — script Python (scripts/backup_db.py)

En Windows, `sqlite3` como CLI puede no estar instalado. Es más
seguro usar el módulo Python `sqlite3` (que sí viene en Python) para
hacer el backup. El script:
1. `sqlite3.connect(source).backup(target)` — copia en caliente segura
2. Verificación de integridad con `PRAGMA integrity_check`
3. Comprime con `gzip` (opcional — SQLite no es muy grande)
4. Rota: 7 diarios, 4 semanales, 3 mensuales
5. Log en `backups/backup.log`

El `backup_db.bat` simplemente llama al `.py` con el venv Python:
```bat
@echo off
cd /d "%~dp0.."
call venv\Scripts\activate.bat
python scripts\backup_db.py
```

---

## Flujo del usuario en Windows 11

1. **Copiar ZIP** a la PC Windows (ej: Escritorio)
2. **Descomprimir** (clic derecho → Extraer todo)
3. **Doble-click en `instalar.bat`**
   - Instala Python si falta
   - Crea venv e instala dependencias
   - Configura .env con password "azul"
   - Inicializa DB si no existe
   - Registra backup automático diario a las 03:00
   - Crea accesos directos
4. **Doble-click en "Azul OS" en el Escritorio**
   - Inicia servidor en localhost:8000
   - Abre el navegador
   - Pide password (azul)
   - Listo para usar

---

## Preguntas antes de proceder

1. **¿Incluyo la DB actual con datos reales en el ZIP?**
   (Opción B) o ¿arranca limpio (Opción A)?

2. **¿Quieres que incluya también el acceso por internet (cloudflared)**
   como el instalador anterior, o solo localhost?

3. **¿El puerto 8000 está bien o prefieres otro?**

4. **¿Quieres que incluya las credenciales de Twilio en el .env**
   o que vengan en blanco para que las complete el usuario?
