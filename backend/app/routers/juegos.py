from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models import Juego, Mobiliario
from app.schemas import JuegoSave, JuegoOut

router = APIRouter(prefix="/juegos", tags=["juegos"])


def _juego_out(j: Juego, db: Session) -> JuegoOut:
    mob = db.query(Mobiliario).filter(Mobiliario.id == j.mobiliario_id).first()
    return JuegoOut(
        id=j.id,
        nombre=j.nombre,
        mobiliario_id=j.mobiliario_id,
        cantidad=j.cantidad,
        precio_alquiler=j.precio_alquiler,
        descripcion=j.descripcion or "",
        activo=j.activo,
        mobiliario_nombre=mob.nombre if mob else "—",
        mobiliario_stock=mob.stock_total if mob else 0,
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
    mob = db.query(Mobiliario).filter(Mobiliario.id == data.mobiliario_id).first()
    if not mob:
        raise HTTPException(400, f"Mobiliario id={data.mobiliario_id} no existe")
    if data.cantidad < 1:
        raise HTTPException(400, "La cantidad debe ser >= 1")
    j = Juego(
        nombre=data.nombre,
        mobiliario_id=data.mobiliario_id,
        cantidad=data.cantidad,
        precio_alquiler=data.precio_alquiler,
        descripcion=data.descripcion,
        activo=data.activo,
    )
    db.add(j)
    db.commit()
    db.refresh(j)
    return _juego_out(j, db)


@router.put("/{juego_id}", response_model=JuegoOut)
def actualizar_juego(juego_id: int, data: JuegoSave, db: Session = Depends(get_db)):
    j = db.query(Juego).filter(Juego.id == juego_id).first()
    if not j:
        raise HTTPException(404, "Juego no encontrado")
    mob = db.query(Mobiliario).filter(Mobiliario.id == data.mobiliario_id).first()
    if not mob:
        raise HTTPException(400, f"Mobiliario id={data.mobiliario_id} no existe")
    if data.cantidad < 1:
        raise HTTPException(400, "La cantidad debe ser >= 1")
    j.nombre = data.nombre
    j.mobiliario_id = data.mobiliario_id
    j.cantidad = data.cantidad
    j.precio_alquiler = data.precio_alquiler
    j.descripcion = data.descripcion
    j.activo = data.activo
    db.commit()
    db.refresh(j)
    return _juego_out(j, db)


@router.delete("/{juego_id}")
def borrar_juego(juego_id: int, db: Session = Depends(get_db)):
    j = db.query(Juego).filter(Juego.id == juego_id).first()
    if not j:
        raise HTTPException(404, "Juego no encontrado")
    db.delete(j)
    db.commit()
    return {"ok": True, "id": juego_id}
