from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date
from app.database import get_db
from app.models import Mobiliario, EventoMobiliario, Evento, EstadoEvento
from app.schemas import MobiliarioOut
import os, uuid, io
from PIL import Image

router = APIRouter(prefix="/mobiliario", tags=["mobiliario"])

# backend/app/routers/mobiliario.py → subir 4 niveles hasta repo root
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
UPLOAD_DIR = os.path.join(PROJECT_ROOT, "uploads", "mobiliario")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ─── COMPRESIÓN DE FOTOS ───
# Guarda DOS versiones:
#   - uploads/mobiliario/        → comprimida (1200px, JPEG q80) para web/app
#   uploads/mobiliario/full/     → original sin modificar para PDF/Word
MAX_FOTO_SIZE = 1200  # px en el lado más largo (versión web)
JPEG_QUALITY = 80
FULL_DIR = os.path.join(UPLOAD_DIR, "full")
os.makedirs(FULL_DIR, exist_ok=True)


def _procesar_y_guardar_foto(foto_file, dest_dir: str) -> str:
    """Lee el UploadFile, guarda el original en full/ y una versión
    comprimida (1200px JPEG q80) en dest_dir.
    Devuelve el nombre del archivo guardado (siempre .jpg)."""
    # Leer el contenido completo a memoria (lo necesitamos 2 veces)
    raw = foto_file.file.read()
    fname = f"{uuid.uuid4().hex}.jpg"

    # 1) Guardar original tal cual en full/
    full_path = os.path.join(FULL_DIR, fname)
    with open(full_path, "wb") as f:
        f.write(raw)

    # 2) Procesar versión comprimida para web
    img = Image.open(io.BytesIO(raw))
    img = img.convert("RGB")
    w, h = img.size
    if max(w, h) > MAX_FOTO_SIZE:
        if w >= h:
            new_w = MAX_FOTO_SIZE
            new_h = int(h * (MAX_FOTO_SIZE / w))
        else:
            new_h = MAX_FOTO_SIZE
            new_w = int(w * (MAX_FOTO_SIZE / h))
        img = img.resize((new_w, new_h), Image.LANCZOS)
    web_path = os.path.join(dest_dir, fname)
    img.save(web_path, "JPEG", quality=JPEG_QUALITY, optimize=True)

    return fname


def _foto_full_path(foto_path: str) -> str:
    """Devuelve la ruta a la versión original (full/) de una foto.
    Si no existe el original, cae back a la versión comprimida."""
    if not foto_path:
        return ""
    full = os.path.join(FULL_DIR, foto_path)
    if os.path.exists(full):
        return full
    # fallback: versión comprimida
    web = os.path.join(UPLOAD_DIR, foto_path)
    return web if os.path.exists(web) else ""


def _stock_disponible(item, db):
    reservado = 0
    ems = db.query(EventoMobiliario).filter(EventoMobiliario.mobiliario_id == item.id).all()
    for em in ems:
        evento = db.query(Evento).filter(Evento.id == em.evento_id).first()
        if evento and evento.estado in ["reserva", "confirmado"]:
            reservado += em.cantidad
    return item.stock_total - reservado


def _mobiliario_out(item, db):
    foto_url = f"/uploads/mobiliario/{item.foto_path}" if item.foto_path else ""
    return MobiliarioOut(
        id=item.id,
        nombre=item.nombre,
        categoria=item.categoria,
        descripcion=item.descripcion,
        precio_alquiler=item.precio_alquiler,
        stock_total=item.stock_total,
        foto_path=item.foto_path or "",
        activo=item.activo,
        stock_disponible=_stock_disponible(item, db),
    )


@router.get("/", response_model=List[MobiliarioOut])
def listar(db: Session = Depends(get_db)):
    items = db.query(Mobiliario).filter(Mobiliario.activo == True).all()
    return [_mobiliario_out(i, db) for i in items]


@router.post("/", response_model=MobiliarioOut)
async def crear(
    nombre: str = Form(...),
    categoria: str = Form(...),
    descripcion: str = Form(""),
    precio_alquiler: float = Form(...),
    stock_total: int = Form(1),
    activo: bool = Form(True),
    foto: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    foto_path = ""
    if foto and foto.filename:
        try:
            foto_path = _procesar_y_guardar_foto(foto, UPLOAD_DIR)
        except Exception as e:
            print(f"[mobiliario] Error procesando foto: {e}")
            foto_path = ""

    item = Mobiliario(
        nombre=nombre,
        categoria=categoria,
        descripcion=descripcion,
        precio_alquiler=precio_alquiler,
        stock_total=stock_total,
        foto_path=foto_path,
        activo=activo,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return _mobiliario_out(item, db)


@router.get("/{item_id}", response_model=MobiliarioOut)
def obtener(item_id: int, db: Session = Depends(get_db)):
    item = db.query(Mobiliario).filter(Mobiliario.id == item_id).first()
    if not item:
        raise HTTPException(404, "Mobiliario no encontrado")
    return _mobiliario_out(item, db)


@router.put("/{item_id}", response_model=MobiliarioOut)
async def actualizar(
    item_id: int,
    nombre: str = Form(...),
    categoria: str = Form(...),
    descripcion: str = Form(""),
    precio_alquiler: float = Form(...),
    stock_total: int = Form(1),
    activo: bool = Form(True),
    foto: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    item = db.query(Mobiliario).filter(Mobiliario.id == item_id).first()
    if not item:
        raise HTTPException(404, "Mobiliario no encontrado")

    item.nombre = nombre
    item.categoria = categoria
    item.descripcion = descripcion
    item.precio_alquiler = precio_alquiler
    item.stock_total = stock_total
    item.activo = activo

    if foto and foto.filename:
        # borrar foto vieja si existe (web + full)
        if item.foto_path:
            for old_path in [os.path.join(UPLOAD_DIR, item.foto_path),
                             os.path.join(FULL_DIR, item.foto_path)]:
                if os.path.exists(old_path):
                    os.remove(old_path)
        try:
            item.foto_path = _procesar_y_guardar_foto(foto, UPLOAD_DIR)
        except Exception as e:
            print(f"[mobiliario] Error procesando foto: {e}")

    db.commit()
    db.refresh(item)
    return _mobiliario_out(item, db)


@router.delete("/{item_id}")
def eliminar(item_id: int, db: Session = Depends(get_db)):
    item = db.query(Mobiliario).filter(Mobiliario.id == item_id).first()
    if not item:
        raise HTTPException(404, "Mobiliario no encontrado")
    item.activo = False
    db.commit()
    return {"ok": True}


# ─── DISPONIBILIDAD POR FECHA ───
@router.get("/disponibilidad/{fecha}")
def consultar_disponibilidad(fecha: date, db: Session = Depends(get_db)):
    """Devuelve el mobiliario disponible para una fecha dada.

    Formato: {fecha, disponible: [{id, nombre, categoria, stock_total,
    disponible, precio}], total_items, eventos_activos}
    """
    eventos = db.query(Evento).filter(
        EstadoEvento.in_([EstadoEvento.reserva, EstadoEvento.confirmado])
    ).all()

    eventos_fecha = []
    for ev in eventos:
        if ev.fecha.date() == fecha:
            eventos_fecha.append(ev)
        elif ev.fecha_fin and ev.fecha.date() <= fecha <= ev.fecha_fin.date():
            eventos_fecha.append(ev)

    comprometido = {}
    for ev in eventos_fecha:
        items = db.query(EventoMobiliario).filter(EventoMobiliario.evento_id == ev.id).all()
        for item in items:
            comprometido[item.mobiliario_id] = comprometido.get(item.mobiliario_id, 0) + item.cantidad

    disponible = []
    mobiliario = db.query(Mobiliario).filter(Mobiliario.activo == True).all()
    for m in mobiliario:
        stock_disponible = m.stock_total - comprometido.get(m.id, 0)
        if stock_disponible > 0:
            disponible.append({
                "id": m.id,
                "nombre": m.nombre,
                "categoria": m.categoria,
                "stock_total": m.stock_total,
                "disponible": stock_disponible,
                "precio": m.precio_alquiler,
            })

    return {
        "fecha": fecha.isoformat(),
        "disponible": disponible,
        "total_items": len(disponible),
        "eventos_activos": len(eventos_fecha),
    }
