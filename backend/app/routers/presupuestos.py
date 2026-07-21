from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime as _dt, date as _date
import json
import os
import tempfile
import zipfile
import io

from app.database import get_db
from app.models import (
    Mobiliario, Cliente, Evento, EventoMobiliario, Presupuesto,
    LogisticaZona, LogisticaServicio, ConfigLogistica,
)
from app.schemas import (
    PresupuestoRequest, PresupuestoResponse, PresupuestoLinea,
    PresupuestoAvanzadoRequest, PresupuestoAvanzadoResponse, LugarCalculado,
    PresupuestoSave, PresupuestoDBOut, LugarPresupuesto, ProductoLugar,
    ZonaOut, ServicioOut, LogisticaConfigOut,
)
from app.pdf_gen import (
    generate_pdf_completo, generate_pdf_cliente, generate_pdf_empleados,
)

router = APIRouter()


# ─── HELPERS DE PRECIO ───
PRECIO_POR_KM_DEFAULT = 7000.0


def _redondear_precio(precio: float) -> float:
    """Redondea un precio al múltiplo 'lindo' más cercano según su magnitud.

    >10000 → múltiplo de 500; >1000 → múltiplo de 100; >100 → múltiplo de 50.
    """
    if precio > 10000:
        multiplo = 500
    elif precio > 1000:
        multiplo = 100
    elif precio > 100:
        multiplo = 50
    else:
        return round(precio)
    return round(precio / multiplo) * multiplo


def calcular_precio_ajustado(precio_base: float, fecha_evento: str) -> float:
    """Aplica el ajuste de 3% por cada mes de diferencia entre hoy y la fecha
    del evento. Si el evento es en el mismo mes o en el pasado, devuelve el
    precio base redondeado.

    El precio en la BD es el precio del mes actual; el ajuste SOLO aplica al
    mostrar/calcular presupuestos, NO se modifica el precio en la BD.
    """
    if not fecha_evento or not precio_base:
        return _redondear_precio(precio_base)

    hoy = _date.today()
    fecha = None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d/%m/%y"):
        try:
            fecha = _dt.strptime(str(fecha_evento).strip(), fmt).date()
            break
        except (ValueError, TypeError):
            continue
    if not fecha:
        return _redondear_precio(precio_base)

    # Si el evento está en el mismo mes o en el pasado, sin ajuste
    if fecha.year < hoy.year or (fecha.year == hoy.year and fecha.month <= hoy.month):
        return _redondear_precio(precio_base)

    # Meses completos de diferencia (julio→diciembre = 5)
    meses = (fecha.year - hoy.year) * 12 + (fecha.month - hoy.month)
    if meses <= 0:
        return _redondear_precio(precio_base)

    precio_ajustado = precio_base * (1 + 0.03 * meses)
    return _redondear_precio(precio_ajustado)


# ─── LOGÍSTICA ───
@router.get("/logistica/", response_model=LogisticaConfigOut)
def get_logistica(db: Session = Depends(get_db)):
    zonas = db.query(LogisticaZona).order_by(LogisticaZona.id).all()
    servicios = db.query(LogisticaServicio).order_by(LogisticaServicio.id).all()
    acarreo_cfg = db.query(ConfigLogistica).filter(ConfigLogistica.clave == "acarreo_adicional").first()
    return LogisticaConfigOut(
        zonas=zonas,
        servicios=servicios,
        acarreo_adicional=acarreo_cfg.valor if acarreo_cfg else 3500.0,
    )


@router.post("/logistica/zonas/", response_model=ZonaOut)
def crear_zona(nombre: str, precio: float = 0.0, db: Session = Depends(get_db)):
    z = LogisticaZona(nombre=nombre, precio=precio)
    db.add(z)
    db.commit()
    db.refresh(z)
    return z


@router.put("/logistica/zonas/{zona_id}", response_model=ZonaOut)
def actualizar_zona(zona_id: int, nombre: Optional[str] = None, precio: Optional[float] = None, db: Session = Depends(get_db)):
    z = db.query(LogisticaZona).filter(LogisticaZona.id == zona_id).first()
    if not z:
        raise HTTPException(404, "Zona no encontrada")
    if nombre is not None:
        z.nombre = nombre
    if precio is not None:
        z.precio = precio
    db.commit()
    db.refresh(z)
    return z


@router.delete("/logistica/zonas/{zona_id}")
def eliminar_zona(zona_id: int, db: Session = Depends(get_db)):
    z = db.query(LogisticaZona).filter(LogisticaZona.id == zona_id).first()
    if not z:
        raise HTTPException(404, "Zona no encontrada")
    db.delete(z)
    db.commit()
    return {"ok": True}


@router.get("/logistica/precio-por-km")
def get_precio_por_km(db: Session = Depends(get_db)):
    cfg = db.query(ConfigLogistica).filter(ConfigLogistica.clave == "precio_por_km").first()
    return {"precio_por_km": cfg.valor if cfg else 7000.0}


@router.put("/logistica/precio-por-km")
def set_precio_por_km(valor: float, db: Session = Depends(get_db)):
    cfg = db.query(ConfigLogistica).filter(ConfigLogistica.clave == "precio_por_km").first()
    if not cfg:
        cfg = ConfigLogistica(clave="precio_por_km", valor=valor)
        db.add(cfg)
    else:
        cfg.valor = valor
    db.commit()
    db.refresh(cfg)
    return {"precio_por_km": cfg.valor}


@router.put("/logistica/acarreo-adicional")
def set_acarreo_adicional(valor: float, db: Session = Depends(get_db)):
    cfg = db.query(ConfigLogistica).filter(ConfigLogistica.clave == "acarreo_adicional").first()
    if not cfg:
        cfg = ConfigLogistica(clave="acarreo_adicional", valor=valor)
        db.add(cfg)
    else:
        cfg.valor = valor
    db.commit()
    db.refresh(cfg)
    return {"acarreo_adicional": cfg.valor}


# ─── PRESUPUESTO SIMPLE (mantiene compatibilidad) ───
@router.post("/calcular-simple/", response_model=PresupuestoResponse)
def calcular_presupuesto_simple(data: PresupuestoRequest, db: Session = Depends(get_db)):
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


# ─── PRESUPUESTO AVANZADO (con lugares + logística automática) ───
@router.post("/calculate/", response_model=PresupuestoAvanzadoResponse)
def calcular_presupuesto_avanzado(data: PresupuestoAvanzadoRequest, db: Session = Depends(get_db)):
    all_mob = db.query(Mobiliario).filter(Mobiliario.activo == True).all()
    mob_by_nombre = {m.nombre: m for m in all_mob}
    mob_by_id = {m.id: m for m in all_mob}

    lugares_calc = []
    subtotal_mobiliario = 0.0

    for lugar in data.lugares:
        productos_calc = []
        subtotal_lugar = 0.0
        for prod in lugar.productos:
            mob = None
            if prod.mobiliario_id:
                mob = mob_by_id.get(prod.mobiliario_id)
                if mob and not prod.catalogo_key:
                    prod.catalogo_key = mob.nombre
            if not mob:
                mob = mob_by_nombre.get(prod.catalogo_key)
            if mob:
                precio_base = prod.precio_manual if prod.precio_manual is not None else mob.precio_alquiler
                precio = calcular_precio_ajustado(precio_base, data.fecha_evento)
                mob_id = mob.id
            else:
                precio = prod.precio_manual if prod.precio_manual is not None else 0.0
                mob_id = 0
            sub = precio * prod.cantidad
            productos_calc.append(PresupuestoLinea(
                mobiliario_id=mob_id,
                nombre=prod.catalogo_key,
                cantidad=prod.cantidad,
                precio_unitario=precio,
                subtotal=sub,
            ))
            subtotal_lugar += sub
        lugares_calc.append(LugarCalculado(
            nombre=lugar.nombre,
            productos=productos_calc,
            subtotal=subtotal_lugar,
        ))
        subtotal_mobiliario += subtotal_lugar

    costo_logistica = 0.0
    costo_zona = 0.0
    costo_servicio = 0.0
    costo_acarreo = 0.0

    # Logística simplificada: distancia_km * precio_por_km (7000 por defecto)
    if data.distancia_km and data.distancia_km > 0:
        cfg_km = db.query(ConfigLogistica).filter(ConfigLogistica.clave == "precio_por_km").first()
        precio_km = cfg_km.valor if cfg_km else PRECIO_POR_KM_DEFAULT
        costo_logistica = data.distancia_km * precio_km
    else:
        # si no hay distancia, usar zona por localidad como fallback razonable
        zona = db.query(LogisticaZona).filter(LogisticaZona.nombre == data.localidad).first()
        if zona:
            costo_zona = zona.precio
        costo_logistica = costo_zona

    total = subtotal_mobiliario + costo_logistica
    total_final = data.total_override if data.total_override else total

    wa = _generar_whatsapp_text(data, lugares_calc, subtotal_mobiliario, costo_logistica, total_final)

    return PresupuestoAvanzadoResponse(
        lugares=lugares_calc,
        subtotal_mobiliario=subtotal_mobiliario,
        costo_zona=costo_zona,
        costo_servicio=costo_servicio,
        costo_acarreo=costo_acarreo,
        costo_logistica=costo_logistica,
        total=total_final,
        total_override=data.total_override,
        whatsapp_text=wa,
    )


# ─── PARSEAR CHAT CON IA ───
@router.post("/from-chat/")
async def parsear_chat(chat_text: str = "", db: Session = Depends(get_db)):
    if not chat_text.strip():
        raise HTTPException(400, "Texto de chat vacío")
    from app.parser import parse_whatsapp_chat
    all_mob = db.query(Mobiliario).filter(Mobiliario.activo == True).all()
    catalog_data = {
        "productos": {m.nombre: {"precio_alquiler": m.precio_alquiler, "categoria": m.categoria} for m in all_mob},
        "logistica": {
            "zonas": {z.nombre: z.precio for z in db.query(LogisticaZona).all()},
            "servicios": {s.nombre: s.precio for s in db.query(LogisticaServicio).all()},
        }
    }
    result = parse_whatsapp_chat(chat_text, catalog_data)
    if "error" in result:
        raise HTTPException(500, result["error"])
    return result


@router.post("/upload-zip/")
async def upload_zip(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.endswith('.zip'):
        raise HTTPException(400, "Solo se aceptan archivos .zip")
    tmp_dir = tempfile.mkdtemp()
    zip_path = os.path.join(tmp_dir, file.filename)
    extract_dir = os.path.join(tmp_dir, "extracted")
    os.makedirs(extract_dir, exist_ok=True)
    with open(zip_path, "wb") as f:
        content = await file.read()
        f.write(content)
    try:
        with zipfile.ZipFile(zip_path, 'r') as z:
            z.extractall(extract_dir)
    except zipfile.BadZipFile:
        raise HTTPException(400, "Archivo ZIP corrupto")

    chat_text = ""
    for root, dirs, files in os.walk(extract_dir):
        for f in sorted(files):
            if f.endswith('.txt') and not f.startswith('__MACOSX'):
                txt_path = os.path.join(root, f)
                with open(txt_path, 'r', encoding='utf-8', errors='ignore') as fh:
                    chat_text = fh.read()
                break

    from app.parser import extract_pdfs_from_dir, preprocess_chat_with_audio, parse_whatsapp_chat
    pdf_context = extract_pdfs_from_dir(extract_dir)
    preprocessed_chat = preprocess_chat_with_audio(chat_text, extract_dir)

    all_mob = db.query(Mobiliario).filter(Mobiliario.activo == True).all()
    catalog_data = {
        "productos": {m.nombre: {"precio_alquiler": m.precio_alquiler, "categoria": m.categoria} for m in all_mob},
        "logistica": {
            "zonas": {z.nombre: z.precio for z in db.query(LogisticaZona).all()},
            "servicios": {s.nombre: s.precio for s in db.query(LogisticaServicio).all()},
        }
    }
    parsed = parse_whatsapp_chat(preprocessed_chat, catalog_data, pdf_context)
    if "error" in parsed:
        raise HTTPException(500, parsed["error"])
    return {"parsed_budget": parsed, "preprocessed_chat": preprocessed_chat, "image_urls": []}


# ─── PDF ENDPOINTS (delegan a pdf_gen.py) ───
def _get_ppto_with_lugares(ppto_id: int, db: Session):
    p = db.query(Presupuesto).filter(Presupuesto.id == ppto_id).first()
    if not p:
        raise HTTPException(404, "Presupuesto no encontrado")
    lugares_data = json.loads(p.lugares_json) if p.lugares_json else []
    ppto_dict = {
        "cliente_nombre": p.cliente_nombre,
        "fecha_evento": p.fecha_evento,
        "tipo_evento": p.tipo_evento,
        "cantidad_invitados": p.cantidad_invitados,
        "localidad": p.localidad,
        "distancia_km": p.distancia_km,
        "subtotal_mobiliario": p.subtotal_mobiliario,
        "costo_logistica": p.costo_logistica,
        "total": p.total,
        "estado": p.estado,
    }
    return p, lugares_data, ppto_dict


def _lookup_mob_prices(db: Session) -> dict:
    all_mob = db.query(Mobiliario).filter(Mobiliario.activo == True).all()
    return {m.nombre: m.precio_alquiler for m in all_mob}


def _lookup_mob_fotos(db: Session) -> dict:
    """Retorna {nombre_mobiliario: ruta_absoluta_foto} para los que tienen foto."""
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    upload_dir = os.path.join(project_root, "uploads", "mobiliario")
    all_mob = db.query(Mobiliario).filter(Mobiliario.activo == True).all()
    fotos = {}
    for m in all_mob:
        if m.foto_path:
            fotos[m.nombre] = os.path.join(upload_dir, m.foto_path)
    return fotos


@router.get("/{ppto_id}/pdf/completo")
def presupuesto_pdf_completo(ppto_id: int, db: Session = Depends(get_db)):
    p, lugares_raw, ppto = _get_ppto_with_lugares(ppto_id, db)
    mob_prices = _lookup_mob_prices(db)
    mob_fotos = _lookup_mob_fotos(db)
    buf = generate_pdf_completo(ppto, lugares_raw, mob_prices, mob_fotos)
    return StreamingResponse(buf, media_type="application/pdf",
                             headers={"Content-Disposition": f'attachment; filename="presupuesto_{ppto_id}_completo.pdf"'})


@router.get("/{ppto_id}/pdf/cliente")
def presupuesto_pdf_cliente(ppto_id: int, db: Session = Depends(get_db)):
    p, lugares_raw, ppto = _get_ppto_with_lugares(ppto_id, db)
    mob_fotos = _lookup_mob_fotos(db)
    buf = generate_pdf_cliente(ppto, lugares_raw, mob_fotos)
    return StreamingResponse(buf, media_type="application/pdf",
                             headers={"Content-Disposition": f'attachment; filename="presupuesto_{ppto_id}_cliente.pdf"'})


@router.get("/{ppto_id}/pdf/empleados")
def presupuesto_pdf_empleados(ppto_id: int, db: Session = Depends(get_db)):
    p, lugares_raw, ppto = _get_ppto_with_lugares(ppto_id, db)
    buf = generate_pdf_empleados(ppto, lugares_raw)
    return StreamingResponse(buf, media_type="application/pdf",
                             headers={"Content-Disposition": f'attachment; filename="presupuesto_{ppto_id}_empleados.pdf"'})


# ─── CRUD PRESUPUESTOS GUARDADOS ───
@router.get("/", response_model=List[PresupuestoDBOut])
def listar_presupuestos(db: Session = Depends(get_db)):
    presupuestos = db.query(Presupuesto).order_by(Presupuesto.created_at.desc()).all()
    return [_presupuesto_to_out(p) for p in presupuestos]


@router.get("/{ppto_id}", response_model=PresupuestoDBOut)
def obtener_presupuesto(ppto_id: int, db: Session = Depends(get_db)):
    p = db.query(Presupuesto).filter(Presupuesto.id == ppto_id).first()
    if not p:
        raise HTTPException(404, "Presupuesto no encontrado")
    return _presupuesto_to_out(p)


@router.post("/", response_model=PresupuestoDBOut)
def guardar_presupuesto(data: PresupuestoSave, db: Session = Depends(get_db)):
    cliente_id = data.cliente_id
    cliente_nombre = data.cliente_nombre

    # Si no hay cliente_id pero hay cliente_nombre, crear el cliente automáticamente
    if not cliente_id and cliente_nombre:
        existente = db.query(Cliente).filter(Cliente.nombre == cliente_nombre).first()
        if existente:
            cliente_id = existente.id
        else:
            cliente = Cliente(nombre=cliente_nombre)
            db.add(cliente)
            db.commit()
            db.refresh(cliente)
            cliente_id = cliente.id

    p = Presupuesto(
        cliente_id=cliente_id,
        cliente_nombre=cliente_nombre,
        fecha_evento=data.fecha_evento,
        tipo_evento=data.tipo_evento,
        cantidad_invitados=data.cantidad_invitados,
        localidad=data.localidad,
        distancia_km=data.distancia_km,
        lugares_json=json.dumps([l.model_dump() for l in data.lugares]),
        subtotal_mobiliario=data.subtotal_mobiliario,
        costo_logistica=data.costo_logistica,
        total=data.total,
        whatsapp_text=data.whatsapp_text,
        estado=data.estado,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return _presupuesto_to_out(p)


@router.put("/{ppto_id}", response_model=PresupuestoDBOut)
def actualizar_presupuesto(ppto_id: int, data: PresupuestoSave, db: Session = Depends(get_db)):
    p = db.query(Presupuesto).filter(Presupuesto.id == ppto_id).first()
    if not p:
        raise HTTPException(404, "Presupuesto no encontrado")
    p.cliente_id = data.cliente_id
    p.cliente_nombre = data.cliente_nombre
    p.fecha_evento = data.fecha_evento
    p.tipo_evento = data.tipo_evento
    p.cantidad_invitados = data.cantidad_invitados
    p.localidad = data.localidad
    p.distancia_km = data.distancia_km
    p.lugares_json = json.dumps([l.model_dump() for l in data.lugares])
    p.subtotal_mobiliario = data.subtotal_mobiliario
    p.costo_logistica = data.costo_logistica
    p.total = data.total
    p.whatsapp_text = data.whatsapp_text
    p.estado = data.estado
    db.commit()
    db.refresh(p)
    return _presupuesto_to_out(p)


@router.delete("/{ppto_id}")
def eliminar_presupuesto(ppto_id: int, db: Session = Depends(get_db)):
    p = db.query(Presupuesto).filter(Presupuesto.id == ppto_id).first()
    if not p:
        raise HTTPException(404, "Presupuesto no encontrado")
    db.delete(p)
    db.commit()
    return {"ok": True}


@router.post("/{ppto_id}/convertir-evento/")
def convertir_a_evento(ppto_id: int, db: Session = Depends(get_db)):
    p = db.query(Presupuesto).filter(Presupuesto.id == ppto_id).first()
    if not p:
        raise HTTPException(404, "Presupuesto no encontrado")

    cliente = None
    if p.cliente_id:
        cliente = db.query(Cliente).filter(Cliente.id == p.cliente_id).first()
    if not cliente and p.cliente_nombre:
        cliente = Cliente(nombre=p.cliente_nombre)
        db.add(cliente)
        db.commit()
        db.refresh(cliente)

    from datetime import datetime as dt
    fecha = dt.now()
    if p.fecha_evento:
        for fmt in ("%d/%m/%y", "%d/%m/%Y", "%Y-%m-%d"):
            try:
                fecha = dt.strptime(p.fecha_evento.strip(), fmt)
                break
            except ValueError:
                continue

    evento = Evento(
        cliente_id=cliente.id if cliente else 1,
        titulo=p.tipo_evento or "Presupuesto",
        fecha=fecha,
        lugar=p.localidad,
        estado="reserva",
        estado_pago="pendiente",
        costo_traslado=p.costo_logistica,
        monto_total=p.subtotal_mobiliario + p.costo_logistica,
    )
    db.add(evento)
    db.commit()
    db.refresh(evento)

    all_mob = db.query(Mobiliario).filter(Mobiliario.activo == True).all()
    mob_by_nombre = {m.nombre: m for m in all_mob}
    mob_by_id = {m.id: m for m in all_mob}

    lugares = json.loads(p.lugares_json) if p.lugares_json else []
    for lugar in lugares:
        for prod in lugar.get("productos", []):
            mob = None
            mid = prod.get("mobiliario_id")
            if mid:
                mob = mob_by_id.get(mid)
            if not mob:
                key = prod.get("catalogo_key", "")
                mob = mob_by_nombre.get(key)
            if mob:
                # Usar precio ajustado por mes (mismo criterio que el presupuesto)
                precio_ajustado = calcular_precio_ajustado(mob.precio_alquiler, p.fecha_evento)
                em = EventoMobiliario(
                    evento_id=evento.id,
                    mobiliario_id=mob.id,
                    cantidad=prod.get("cantidad", 1),
                    precio_unitario=precio_ajustado,
                )
                db.add(em)

    from app.routers.eventos import _recalcular_evento
    _recalcular_evento(evento, db)

    p.evento_id = evento.id
    p.estado = "confirmado"
    db.commit()
    return {"ok": True, "evento_id": evento.id}


# ─── HELPERS ───
def _presupuesto_to_out(p: Presupuesto) -> PresupuestoDBOut:
    lugares_data = json.loads(p.lugares_json) if p.lugares_json else []
    lugares = [LugarPresupuesto(**l) for l in lugares_data]
    return PresupuestoDBOut(
        id=p.id,
        cliente_id=p.cliente_id,
        cliente_nombre=p.cliente_nombre,
        fecha_evento=p.fecha_evento,
        tipo_evento=p.tipo_evento,
        cantidad_invitados=p.cantidad_invitados,
        localidad=p.localidad,
        distancia_km=p.distancia_km,
        lugares=lugares,
        subtotal_mobiliario=p.subtotal_mobiliario,
        costo_logistica=p.costo_logistica,
        total=p.total,
        whatsapp_text=p.whatsapp_text,
        estado=p.estado,
        evento_id=p.evento_id,
        created_at=p.created_at,
    )


def _generar_whatsapp_text(data, lugares_calc, subtotal_mob, costo_log, total) -> str:
    lines = []
    lines.append("*AZUL LIVINGS LUJÁN*")
    lines.append("Presupuesto de Alquiler")
    lines.append("")
    if data.cliente_nombre:
        lines.append(f"CLIENTE: {data.cliente_nombre}")
    if data.fecha_evento:
        lines.append(f"FECHA: {data.fecha_evento}")
    if data.tipo_evento:
        lines.append(f"TIPO: {data.tipo_evento}")
    if data.cantidad_invitados:
        lines.append(f"INVITADOS: {data.cantidad_invitados}")
    lines.append("")
    for lugar in lugares_calc:
        if lugar.productos:
            lines.append(f"▸ {lugar.nombre}:")
            for p in lugar.productos:
                lines.append(f"  *{p.cantidad} {p.nombre} — ${int(p.subtotal):,}*".replace(",", "."))
            lines.append("")
    lines.append("─" * 30)
    lines.append(f"Mobiliario: ${int(subtotal_mob):,}".replace(",", "."))
    lines.append(f"Logística: ${int(costo_log):,}".replace(",", "."))
    lines.append("")
    lines.append(f"*TOTAL: ${int(total):,}*".replace(",", "."))
    lines.append("")
    lines.append("_Seña del 50% para confirmar la reserva_")
    return "\n".join(lines)
