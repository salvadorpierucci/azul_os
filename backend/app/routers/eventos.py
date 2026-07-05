from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, date
from app.database import get_db
from app.models import Cliente, Evento, EventoMobiliario, Mobiliario, EstadoEvento
from app.schemas import (
    ClienteCreate, ClienteOut,
    EventoCreate, EventoOut, EventoUpdate,
    EventoMobiliarioCreate, EventoMobiliarioOut,
    PresupuestoRequest, PresupuestoResponse, PresupuestoLinea,
    EventoDetalleOut,
)

router = APIRouter()


# ─── CLIENTES ───
@router.get("/clientes/", response_model=List[ClienteOut])
def listar_clientes(db: Session = Depends(get_db)):
    return db.query(Cliente).order_by(Cliente.nombre).all()


@router.post("/clientes/", response_model=ClienteOut)
def crear_cliente(data: ClienteCreate, db: Session = Depends(get_db)):
    cliente = Cliente(**data.model_dump())
    db.add(cliente)
    db.commit()
    db.refresh(cliente)
    return cliente


@router.get("/clientes/{cliente_id}", response_model=ClienteOut)
def obtener_cliente(cliente_id: int, db: Session = Depends(get_db)):
    c = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not c:
        raise HTTPException(404, "Cliente no encontrado")
    return c


@router.get("/clientes/{cliente_id}/eventos", response_model=List[EventoDetalleOut])
def eventos_por_cliente(cliente_id: int, db: Session = Depends(get_db)):
    """Historial de eventos de un cliente."""
    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not cliente:
        raise HTTPException(404, "Cliente no encontrado")
    eventos = db.query(Evento).filter(Evento.cliente_id == cliente_id).order_by(Evento.fecha.desc()).all()
    result = []
    for ev in eventos:
        ems = db.query(EventoMobiliario).filter(EventoMobiliario.evento_id == ev.id).all()
        items = []
        for em in ems:
            mob = db.query(Mobiliario).filter(Mobiliario.id == em.mobiliario_id).first()
            items.append({
                "id": em.id,
                "mobiliario_id": em.mobiliario_id,
                "nombre": mob.nombre if mob else "Eliminado",
                "categoria": mob.categoria if mob else "",
                "cantidad": em.cantidad,
                "precio_unitario": em.precio_unitario,
                "subtotal": em.cantidad * em.precio_unitario,
            })
        result.append(EventoDetalleOut(
            id=ev.id, cliente_id=ev.cliente_id, cliente_nombre=cliente.nombre,
            titulo=ev.titulo, fecha=ev.fecha, fecha_fin=ev.fecha_fin,
            lugar=ev.lugar, estado=ev.estado, estado_pago=ev.estado_pago,
            costo_traslado=ev.costo_traslado, costo_mano_obra=ev.costo_mano_obra,
            monto_total=ev.monto_total, monto_senia=ev.monto_senia,
            notas=ev.notas, created_at=ev.created_at, items=items,
        ))
    return result


@router.get("/clientes/{cliente_id}/presupuestos")
def presupuestos_por_cliente(cliente_id: int, db: Session = Depends(get_db)):
    """Presupuestos guardados de un cliente."""
    from app.models import Presupuesto
    from app.schemas import PresupuestoDBOut, LugarPresupuesto
    import json
    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not cliente:
        raise HTTPException(404, "Cliente no encontrado")
    presupuestos = db.query(Presupuesto).filter(Presupuesto.cliente_id == cliente_id).order_by(Presupuesto.created_at.desc()).all()
    result = []
    for p in presupuestos:
        lugares_data = json.loads(p.lugares_json) if p.lugares_json else []
        lugares = [LugarPresupuesto(**l) for l in lugares_data]
        result.append(PresupuestoDBOut(
            id=p.id, cliente_id=p.cliente_id, cliente_nombre=p.cliente_nombre,
            fecha_evento=p.fecha_evento, tipo_evento=p.tipo_evento,
            cantidad_invitados=p.cantidad_invitados, localidad=p.localidad,
            distancia_km=p.distancia_km,
            lugares=lugares, subtotal_mobiliario=p.subtotal_mobiliario,
            costo_logistica=p.costo_logistica, total=p.total,
            whatsapp_text=p.whatsapp_text, estado=p.estado,
            evento_id=p.evento_id, created_at=p.created_at,
        ))
    return result


@router.get("/clientes/{cliente_id}/perfil")
def perfil_cliente(cliente_id: int, db: Session = Depends(get_db)):
    """Perfil completo: datos + eventos + presupuestos."""
    from app.models import Presupuesto
    from app.schemas import PresupuestoDBOut, LugarPresupuesto
    import json as _json
    c = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not c:
        raise HTTPException(404, "Cliente no encontrado")
    # eventos
    eventos = db.query(Evento).filter(Evento.cliente_id == cliente_id).order_by(Evento.fecha.desc()).all()
    eventos_out = []
    for ev in eventos:
        eventos_out.append({
            "id": ev.id, "titulo": ev.titulo, "fecha": ev.fecha.isoformat() if ev.fecha else None,
            "estado": ev.estado.value if hasattr(ev.estado, 'value') else str(ev.estado),
            "estado_pago": ev.estado_pago.value if hasattr(ev.estado_pago, 'value') else str(ev.estado_pago),
            "monto_total": ev.monto_total, "lugar": ev.lugar,
        })
    # presupuestos
    presupuestos = db.query(Presupuesto).filter(Presupuesto.cliente_id == cliente_id).order_by(Presupuesto.created_at.desc()).all()
    presupuestos_out = []
    for p in presupuestos:
        presupuestos_out.append({
            "id": p.id, "tipo_evento": p.tipo_evento, "fecha_evento": p.fecha_evento,
            "total": p.total, "estado": p.estado, "created_at": p.created_at.isoformat() if p.created_at else None,
        })
    # resumen financiero
    total_eventos = len(eventos)
    total_gastado = sum(e.monto_total or 0 for e in eventos)
    return {
        "id": c.id, "nombre": c.nombre, "telefono": c.telefono,
        "email": c.email, "whatsapp": c.whatsapp, "notas": c.notas,
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "total_eventos": total_eventos,
        "total_gastado": total_gastado,
        "eventos": eventos_out,
        "presupuestos": presupuestos_out,
    }


@router.put("/clientes/{cliente_id}", response_model=ClienteOut)
def actualizar_cliente(cliente_id: int, data: ClienteCreate, db: Session = Depends(get_db)):
    c = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not c:
        raise HTTPException(404, "Cliente no encontrado")
    for key, value in data.model_dump().items():
        setattr(c, key, value)
    db.commit()
    db.refresh(c)
    return c


@router.delete("/clientes/{cliente_id}")
def eliminar_cliente(cliente_id: int, db: Session = Depends(get_db)):
    c = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not c:
        raise HTTPException(404, "Cliente no encontrado")
    # verificar si tiene eventos
    eventos = db.query(Evento).filter(Evento.cliente_id == cliente_id).count()
    if eventos > 0:
        raise HTTPException(400, f"El cliente tiene {eventos} eventos asociados. Elimine o reasigne los eventos primero.")
    db.delete(c)
    db.commit()
    return {"ok": True}


# ─── EVENTOS ───
@router.get("/eventos/", response_model=List[EventoOut])
def listar_eventos(
    estado: Optional[str] = None,
    desde: Optional[str] = None,
    hasta: Optional[str] = None,
    db: Session = Depends(get_db)
):
    q = db.query(Evento)
    if estado:
        q = q.filter(Evento.estado == estado)
    if desde:
        q = q.filter(Evento.fecha >= datetime.fromisoformat(desde))
    if hasta:
        q = q.filter(Evento.fecha <= datetime.fromisoformat(hasta))
    return q.order_by(Evento.fecha).all()


@router.post("/eventos/", response_model=EventoOut)
def crear_evento(data: EventoCreate, db: Session = Depends(get_db)):
    evento = Evento(**data.model_dump())
    db.add(evento)
    db.commit()
    db.refresh(evento)
    return evento


@router.get("/eventos/{evento_id}", response_model=EventoDetalleOut)
def obtener_evento(evento_id: int, db: Session = Depends(get_db)):
    evento = db.query(Evento).filter(Evento.id == evento_id).first()
    if not evento:
        raise HTTPException(404, "Evento no encontrado")
    # obtener items del evento
    ems = db.query(EventoMobiliario).filter(EventoMobiliario.evento_id == evento_id).all()
    items = []
    for em in ems:
        mob = db.query(Mobiliario).filter(Mobiliario.id == em.mobiliario_id).first()
        items.append({
            "id": em.id,
            "mobiliario_id": em.mobiliario_id,
            "nombre": mob.nombre if mob else "Eliminado",
            "categoria": mob.categoria if mob else "",
            "cantidad": em.cantidad,
            "precio_unitario": em.precio_unitario,
            "subtotal": em.cantidad * em.precio_unitario,
        })
    cliente = db.query(Cliente).filter(Cliente.id == evento.cliente_id).first()
    return EventoDetalleOut(
        id=evento.id,
        cliente_id=evento.cliente_id,
        cliente_nombre=cliente.nombre if cliente else "",
        titulo=evento.titulo,
        fecha=evento.fecha,
        fecha_fin=evento.fecha_fin,
        lugar=evento.lugar,
        estado=evento.estado,
        estado_pago=evento.estado_pago,
        costo_traslado=evento.costo_traslado,
        costo_mano_obra=evento.costo_mano_obra,
        monto_total=evento.monto_total,
        monto_senia=evento.monto_senia,
        notas=evento.notas,
        created_at=evento.created_at,
        items=items,
    )


@router.put("/eventos/{evento_id}", response_model=EventoOut)
def actualizar_evento(evento_id: int, data: EventoUpdate, db: Session = Depends(get_db)):
    evento = db.query(Evento).filter(Evento.id == evento_id).first()
    if not evento:
        raise HTTPException(404, "Evento no encontrado")
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(evento, key, value)
    db.commit()
    db.refresh(evento)
    return evento


@router.delete("/eventos/{evento_id}")
def eliminar_evento(evento_id: int, db: Session = Depends(get_db)):
    evento = db.query(Evento).filter(Evento.id == evento_id).first()
    if not evento:
        raise HTTPException(404, "Evento no encontrado")
    # borrar items asociados
    db.query(EventoMobiliario).filter(EventoMobiliario.evento_id == evento_id).delete()
    db.delete(evento)
    db.commit()
    return {"ok": True}


# ─── DISPONIBILIDAD ───
@router.get("/disponibilidad/{fecha}")
def consultar_disponibilidad(fecha: date, db: Session = Depends(get_db)):
    """Consulta mobiliario disponible para una fecha específica.
    
    Calcula el stock comprometido en eventos confirmados/reservados y retorna
    el mobiliario disponible para esa fecha.
    """
    # Obtener eventos en esa fecha (o eventos que se solapen con esa fecha)
    eventos = db.query(Evento).filter(
        EstadoEvento.in_([EstadoEvento.reserva, EstadoEvento.confirmado])
    ).all()
    
    # Filtrar eventos que incluyen esta fecha
    eventos_fecha = []
    for ev in eventos:
        if ev.fecha.date() == fecha:
            eventos_fecha.append(ev)
        elif ev.fecha_fin and ev.fecha.date() <= fecha <= ev.fecha_fin.date():
            eventos_fecha.append(ev)
    
    # Obtener mobiliario comprometido
    comprometido = {}
    for ev in eventos_fecha:
        items = db.query(EventoMobiliario).filter(EventoMobiliario.evento_id == ev.id).all()
        for item in items:
            comprometido[item.mobiliario_id] = comprometido.get(item.mobiliario_id, 0) + item.cantidad
    
    # Calcular disponible
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
                "precio": m.precio_alquiler
            })
    
    return {
        "fecha": fecha.isoformat(),
        "disponible": disponible,
        "total_items": len(disponible),
        "eventos_activos": len(eventos_fecha)
    }


# ─── EVENTO-MOBILIARIO ───
@router.post("/eventos/{evento_id}/mobiliario/", response_model=EventoMobiliarioOut)
def agregar_mobiliario(evento_id: int, data: EventoMobiliarioCreate, db: Session = Depends(get_db)):
    evento = db.query(Evento).filter(Evento.id == evento_id).first()
    if not evento:
        raise HTTPException(404, "Evento no encontrado")
    mob = db.query(Mobiliario).filter(Mobiliario.id == data.mobiliario_id).first()
    if not mob:
        raise HTTPException(404, "Mobiliario no encontrado")
    em = EventoMobiliario(
        evento_id=evento_id,
        mobiliario_id=data.mobiliario_id,
        cantidad=data.cantidad,
        precio_unitario=mob.precio_alquiler
    )
    db.add(em)
    _recalcular_evento(evento, db)
    db.commit()
    db.refresh(em)
    return em


@router.delete("/eventos/{evento_id}/mobiliario/{em_id}")
def quitar_mobiliario(evento_id: int, em_id: int, db: Session = Depends(get_db)):
    em = db.query(EventoMobiliario).filter(EventoMobiliario.id == em_id).first()
    if not em:
        raise HTTPException(404, "Registro no encontrado")
    db.delete(em)
    evento = db.query(Evento).filter(Evento.id == evento_id).first()
    if evento:
        _recalcular_evento(evento, db)
    db.commit()
    return {"ok": True}


# ─── PRESUPUESTO ───
@router.post("/presupuesto/", response_model=PresupuestoResponse)
def calcular_presupuesto(data: PresupuestoRequest, db: Session = Depends(get_db)):
    lineas = []
    subtotal = 0.0
    for item in data.items:
        mob = db.query(Mobiliario).filter(Mobiliario.id == item.mobiliario_id).first()
        if not mob:
            raise HTTPException(404, f"Mobiliario {item.mobiliario_id} no encontrado")
        linea = PresupuestoLinea(
            mobiliario_id=mob.id,
            nombre=mob.nombre,
            cantidad=item.cantidad,
            precio_unitario=mob.precio_alquiler,
            subtotal=mob.precio_alquiler * item.cantidad
        )
        lineas.append(linea)
        subtotal += linea.subtotal
    total = subtotal + data.costo_traslado + data.costo_mano_obra
    return PresupuestoResponse(
        items=lineas,
        subtotal_mobiliario=subtotal,
        costo_traslado=data.costo_traslado,
        costo_mano_obra=data.costo_mano_obra,
        total=total
    )


def _recalcular_evento(evento: Evento, db: Session):
    ems = db.query(EventoMobiliario).filter(EventoMobiliario.evento_id == evento.id).all()
    evento.monto_total = sum(em.cantidad * em.precio_unitario for em in ems) + evento.costo_traslado + evento.costo_mano_obra
