from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models import Juego, JuegoItem, Mobiliario
from app.schemas import JuegoSave, JuegoOut, JuegoItemOut, JuegoUpdate

router = APIRouter(prefix="/juegos", tags=["juegos"])


def _juego_out(j: Juego, db: Session) -> JuegoOut:
    items_out = []
    for it in j.items:
        mob = db.query(Mobiliario).filter(Mobiliario.id == it.mobiliario_id).first()
        items_out.append(JuegoItemOut(
            id=it.id,
            mobiliario_id=it.mobiliario_id,
            cantidad=it.cantidad,
            mobiliario_nombre=mob.nombre if mob else "—",
            mobiliario_stock=mob.stock_total if mob else 0,
        ))
    return JuegoOut(
        id=j.id,
        nombre=j.nombre,
        precio_alquiler=j.precio_alquiler,
        descripcion=j.descripcion or "",
        activo=j.activo,
        items=items_out,
    )


@router.get("", response_model=List[JuegoOut])
def listar_juegos(solo_activos: bool = False, db: Session = Depends(get_db)):
    q = db.query(Juego)
    if solo_activos:
        q = q.filter(Juego.activo == True)
    juegos = q.all()
    return [_juego_out(j, db) for j in juegos]


@router.get("/{juego_id}", response_model=JuegoOut)
def obtener_juego(juego_id: int, db: Session = Depends(get_db)):
    j = db.query(Juego).filter(Juego.id == juego_id).first()
    if not j:
        raise HTTPException(404, "Juego no encontrado")
    return _juego_out(j, db)


@router.post("", response_model=JuegoOut)
def crear_juego(data: JuegoSave, db: Session = Depends(get_db)):
    if not data.items or len(data.items) == 0:
        raise HTTPException(400, "El juego debe tener al menos un item")
    # Validar que los mobiliarios existen
    for it in data.items:
        mob = db.query(Mobiliario).filter(Mobiliario.id == it.mobiliario_id).first()
        if not mob:
            raise HTTPException(400, f"Mobiliario id={it.mobiliario_id} no existe")
    j = Juego(
        nombre=data.nombre,
        precio_alquiler=data.precio_alquiler,
        descripcion=data.descripcion or "",
        activo=data.activo,
    )
    db.add(j)
    db.flush()  # obtener j.id
    for it in data.items:
        db.add(JuegoItem(
            juego_id=j.id,
            mobiliario_id=it.mobiliario_id,
            cantidad=it.cantidad,
        ))
    db.commit()
    db.refresh(j)
    return _juego_out(j, db)


@router.put("/{juego_id}", response_model=JuegoOut)
def actualizar_juego(juego_id: int, data: JuegoSave, db: Session = Depends(get_db)):
    j = db.query(Juego).filter(Juego.id == juego_id).first()
    if not j:
        raise HTTPException(404, "Juego no encontrado")
    if not data.items or len(data.items) == 0:
        raise HTTPException(400, "El juego debe tener al menos un item")
    for it in data.items:
        mob = db.query(Mobiliario).filter(Mobiliario.id == it.mobiliario_id).first()
        if not mob:
            raise HTTPException(400, f"Mobiliario id={it.mobiliario_id} no existe")
    j.nombre = data.nombre
    j.precio_alquiler = data.precio_alquiler
    j.descripcion = data.descripcion or ""
    j.activo = data.activo
    # Borrar items viejos y crear nuevos
    db.query(JuegoItem).filter(JuegoItem.juego_id == juego_id).delete()
    for it in data.items:
        db.add(JuegoItem(
            juego_id=juego_id,
            mobiliario_id=it.mobiliario_id,
            cantidad=it.cantidad,
        ))
    db.commit()
    db.refresh(j)
    return _juego_out(j, db)


@router.delete("/{juego_id}")
def borrar_juego(juego_id: int, db: Session = Depends(get_db)):
    j = db.query(Juego).filter(Juego.id == juego_id).first()
    if not j:
        raise HTTPException(404, "Juego no encontrado")
    # Los JuegoItem se borran solos por ondelete=CASCADE
    db.delete(j)
    db.commit()
    return {"ok": True, "id": juego_id}
