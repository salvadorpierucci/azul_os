from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models import RegistroFinanciero
from app.schemas import RegistroFinancieroCreate, RegistroFinancieroOut

router = APIRouter(prefix="/finanzas", tags=["finanzas"])


@router.get("/", response_model=List[RegistroFinancieroOut])
def listar(db: Session = Depends(get_db)):
    return db.query(RegistroFinanciero).order_by(RegistroFinanciero.fecha.desc()).all()


@router.post("/", response_model=RegistroFinancieroOut)
def crear(data: RegistroFinancieroCreate, db: Session = Depends(get_db)):
    reg = RegistroFinanciero(**data.model_dump())
    db.add(reg)
    db.commit()
    db.refresh(reg)
    return reg


@router.get("/resumen/mensual")
def resumen_mensual(anio: int = None, mes: int = None, db: Session = Depends(get_db)):
    from sqlalchemy import extract, func
    from datetime import datetime
    now = datetime.now()
    anio = anio or now.year
    mes = mes or now.month
    ingresos = db.query(func.sum(RegistroFinanciero.monto)).filter(
        RegistroFinanciero.tipo == "ingreso",
        extract("year", RegistroFinanciero.fecha) == anio,
        extract("month", RegistroFinanciero.fecha) == mes,
    ).scalar() or 0
    egresos = db.query(func.sum(RegistroFinanciero.monto)).filter(
        RegistroFinanciero.tipo == "egreso",
        extract("year", RegistroFinanciero.fecha) == anio,
        extract("month", RegistroFinanciero.fecha) == mes,
    ).scalar() or 0
    return {
        "anio": anio,
        "mes": mes,
        "ingresos": ingresos,
        "egresos": egresos,
        "balance": ingresos - egresos
    }


@router.delete("/{registro_id}")
def eliminar(registro_id: int, db: Session = Depends(get_db)):
    reg = db.query(RegistroFinanciero).filter(RegistroFinanciero.id == registro_id).first()
    if not reg:
        raise HTTPException(404, "Registro no encontrado")
    db.delete(reg)
    db.commit()
    return {"ok": True}
