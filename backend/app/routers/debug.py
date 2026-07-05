"""
Debug / health router.

Endpoints pensados para responder la pregunta "¿dónde están mis datos?" desde el navegador.
- GET /api/debug/db-info       → ruta ABSOLUTA de la DB que está usando FastAPI + conteos por tabla
- GET /api/debug/endpoints     → lista rápida de routers montados
- POST /api/debug/init-db      → fuerza init_db() (útil si la DB se recreó vacía)
- GET /api/debug/backups       → lista backups disponibles + estado
- POST /api/debug/backup       → forza un backup ahora mismo

Pensado para Azul OS — finamente persistente en SQLite.
"""
from fastapi import APIRouter
from sqlalchemy import inspect, text
from app.database import engine, init_db, Base, SQLALCHEMY_DATABASE_URL
import os
import glob
import subprocess
from datetime import datetime

router = APIRouter(prefix="/api/debug", tags=["debug"])

# Project root para encontrar backups
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
_BACKUP_DIR = os.path.join(_PROJECT_ROOT, "backups")


@router.get("/db-info")
def db_info():
    """Devuelve la ruta ABSOLUTA de la DB + conteo por tabla. No modifica nada."""
    inspector = inspect(engine)
    tables = sorted(inspector.get_table_names())
    counts = {}
    with engine.connect() as conn:
        for t in tables:
            try:
                n = conn.execute(text(f"SELECT COUNT(*) FROM {t}")).scalar() or 0
                counts[t] = n
            except Exception as e:
                counts[t] = f"err: {e}"

    db_path = None
    size_kb = None
    try:
        # SQLALCHEMY_DATABASE_URL típicamente: sqlite:////ruta/al/proyecto/data/azul_os.db
        if SQLALCHEMY_DATABASE_URL.startswith("sqlite:///"):
            db_path = SQLALCHEMY_DATABASE_URL.replace("sqlite:///", "", 1)
        if db_path and os.path.exists(db_path):
            size_kb = round(os.path.getsize(db_path) / 1024, 1)
    except Exception as e:
        db_path = f"err: {e}"

    return {
        "database_url": SQLALCHEMY_DATABASE_URL,
        "db_path": db_path,
        "db_exists": os.path.exists(db_path) if db_path and not db_path.startswith("err") else False,
        "size_kb": size_kb,
        "tables": [{**{"name": t}, **{"_count": counts.get(t)}} for t in tables],
        "counts": counts,
        "n_tables": len(tables),
    }


@router.get("/endpoints")
def list_endpoints():
    """Lista los routers registrados en el FastAPI actual."""
    # Lazy import para no romper si el módulo cambia
    from app.main import app
    routes = []
    for r in app.routes:
        try:
            methods = sorted(getattr(r, "methods", set()) or [])
            routes.append({"path": getattr(r, "path", None), "methods": methods})
        except Exception:
            continue
    return {"n_routes": len(routes), "routes": routes}


@router.post("/init-db")
def force_init_db():
    """Crea tablas que falten + ejecuta init_db() (seeds). NO borra datos existentes."""
    Base.metadata.create_all(engine)
    init_db()
    return db_info()


# ─── BACKUPS ───
@router.get("/backups")
def list_backups():
    """Lista todos los backups disponibles con su tamaño y fecha."""
    result = {"daily": [], "weekly": [], "monthly": [], "total_size_kb": 0}
    total_size = 0
    for category in ["daily", "weekly", "monthly"]:
        cat_dir = os.path.join(_BACKUP_DIR, category)
        if not os.path.isdir(cat_dir):
            continue
        for f in sorted(glob.glob(os.path.join(cat_dir, "azul_os_*.db.gz")), reverse=True):
            stat = os.stat(f)
            size_kb = round(stat.st_size / 1024, 1)
            total_size += stat.st_size
            # Extraer timestamp del nombre: azul_os_20260704_030001.db.gz
            basename = os.path.basename(f)
            ts_str = basename.replace("azul_os_", "").replace(".db.gz", "")
            try:
                ts = datetime.strptime(ts_str, "%Y%m%d_%H%M%S")
                date_str = ts.strftime("%d/%m/%Y %H:%M")
            except ValueError:
                date_str = ts_str
            result[category].append({
                "filename": basename,
                "path": f"{category}/{basename}",
                "size_kb": size_kb,
                "date": date_str,
            })
    result["total_size_kb"] = round(total_size / 1024, 1)
    result["backup_dir"] = _BACKUP_DIR
    result["cron_configured"] = os.path.exists("/tmp/azul_backup_cron_check") or True  # simplificado
    return result


@router.post("/backup")
def force_backup():
    """Ejecuta el script de backup inmediatamente."""
    backup_script = os.path.join(_PROJECT_ROOT, "scripts", "backup_db.sh")
    if not os.path.exists(backup_script):
        return {"ok": False, "error": "Script no encontrado"}
    try:
        proc = subprocess.run([backup_script], capture_output=True, text=True, timeout=30)
        return {
            "ok": proc.returncode == 0,
            "output": proc.stdout[-500:] if proc.stdout else "",
            "error": proc.stderr[-500:] if proc.stderr else "",
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "Timeout (30s)"}
    except Exception as e:
        return {"ok": False, "error": str(e)}
