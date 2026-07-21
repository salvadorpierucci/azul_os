from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Depends, HTTPException, status
import os
import secrets
from dotenv import load_dotenv

# Cargar .env: primero backend/.env, luego ~/.config/azul-os/.env (Linux)
_env_local = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
_env_home = os.path.expanduser("~/.config/azul-os/.env")
if os.path.exists(_env_local):
    load_dotenv(_env_local)
elif os.path.exists(_env_home):
    load_dotenv(_env_home)
else:
    load_dotenv()

from app.database import init_db
from app.routers import mobiliario, eventos, finanzas, presupuestos, debug
from app.routers import whatsapp_twilio as whatsapp
from app.auth import AuthMiddleware, login_endpoint, logout_endpoint, login_page

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FRONTEND_DIR = os.path.join(PROJECT_ROOT, "frontend")

app = FastAPI(title="Azul OS", version="0.2.0")

# CORS — restringir origins según AZUL_CORS_ORIGINS (comma-separated)
# Default: solo localhost y LAN
_cors_env = os.environ.get("AZUL_CORS_ORIGINS", "")
if _cors_env:
    _allowed_origins = [o.strip() for o in _cors_env.split(",")]
else:
    _allowed_origins = [
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Auth middleware — simple bearer token
app.add_middleware(AuthMiddleware)

# API routers
app.include_router(mobiliario.router, prefix="/api")
app.include_router(eventos.router, prefix="/api")
app.include_router(finanzas.router, prefix="/api")
app.include_router(presupuestos.router, prefix="/api/presupuestos", tags=["Presupuestos"])
app.include_router(whatsapp.router)  # /whatsapp/* directo, no bajo /api
app.include_router(debug.router)    # /api/debug/* — health & diagnóstico

# uploads folder for mobiliario photos
UPLOAD_DIR = os.path.join(PROJECT_ROOT, "uploads", "mobiliario")
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=os.path.join(PROJECT_ROOT, "uploads")), name="uploads")


@app.get("/")
async def serve_index():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))


# Archivos estaticos
_css_dir = os.path.join(FRONTEND_DIR, "css")
_js_dir = os.path.join(FRONTEND_DIR, "js")

if os.path.isdir(_css_dir):
    app.mount("/css", StaticFiles(directory=_css_dir), name="css")
if os.path.isdir(_js_dir):
    app.mount("/js", StaticFiles(directory=_js_dir), name="js")


@app.get("/login")
async def serve_login():
    return login_page()


@app.post("/login")
async def do_login(request: Request):
    return await login_endpoint(request)


@app.post("/logout")
async def do_logout():
    return await logout_endpoint()


@app.on_event("startup")
def startup():
    init_db()
    # Backup automatico al iniciar (extra safety ante cortes de luz)
    # Usa backup_db.py si existe (cross-platform), sino backup_db.sh (Linux)
    import subprocess, sys
    backup_py = os.path.join(PROJECT_ROOT, "scripts", "backup_db.py")
    backup_sh = os.path.join(PROJECT_ROOT, "scripts", "backup_db.sh")
    if os.path.exists(backup_py):
        try:
            subprocess.run([sys.executable, backup_py], capture_output=True, timeout=30)
        except Exception:
            pass
    elif os.path.exists(backup_sh):
        try:
            subprocess.run([backup_sh], capture_output=True, timeout=30)
        except Exception:
            pass
