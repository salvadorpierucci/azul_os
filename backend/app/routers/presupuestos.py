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
    LogisticaZona, LogisticaServicio, ConfigLogistica, Juego, JuegoItem,
)
from app.schemas import (
    PresupuestoRequest, PresupuestoResponse, PresupuestoLinea,
    PresupuestoAvanzadoRequest, PresupuestoAvanzadoResponse, LugarCalculado,
    PresupuestoSave, PresupuestoDBOut, LugarPresupuesto, ProductoLugar,
    ZonaOut, ServicioOut, LogisticaConfigOut,
)


def _enriquecer_productos_con_precios(lugares, db: Session, fecha_evento: str) -> list:
    """Toma una lista de LugarPresupuesto (o dicts crudos) y devuelve una lista
    de dicts con el JSON de cada lugar, agregando `precio_unitario` y `subtotal`
    a cada producto, ya sea mobiliario o juego. Aplica el ajuste 3% mensual.
    También inyecta `nombre` para que el frontend pueda mostrarlo si no está.
    """
    all_mob = db.query(Mobiliario).filter(Mobiliario.activo == True).all()
    mob_by_id = {m.id: m for m in all_mob}
    mob_by_nombre = {m.nombre: m for m in all_mob}
    all_juegos = db.query(Juego).filter(Juego.activo == True).all()
    juego_by_id = {j.id: j for j in all_juegos}

    enriched = []
    for lug in lugares:
        lug_dict = {
            "nombre": getattr(lug, "nombre", "") or (lug.get("nombre", "") if isinstance(lug, dict) else ""),
            "productos": []
        }
        productos = getattr(lug, "productos", None) or (lug.get("productos", []) if isinstance(lug, dict) else [])
        for prod in productos:
            p = prod if isinstance(prod, dict) else prod.model_dump()
            precio = 0.0
            cantidad = p.get("cantidad", 1) or 1
            if p.get("juego_id"):
                juego = juego_by_id.get(p["juego_id"])
                if juego:
                    precio_base = p.get("precio_manual") if p.get("precio_manual") is not None else juego.precio_alquiler
                    precio = calcular_precio_ajustado(precio_base, fecha_evento)
            elif p.get("mobiliario_id"):
                mob = mob_by_id.get(p["mobiliario_id"])
                if not mob:
                    key = p.get("catalogo_key", "")
                    if key:
                        mob = mob_by_nombre.get(key)
                if mob:
                    precio_base = p.get("precio_manual") if p.get("precio_manual") is not None else mob.precio_alquiler
                    precio = calcular_precio_ajustado(precio_base, fecha_evento)
            elif p.get("catalogo_key"):
                mob = mob_by_nombre.get(p["catalogo_key"])
                if mob:
                    precio_base = p.get("precio_manual") if p.get("precio_manual") is not None else mob.precio_alquiler
                    precio = calcular_precio_ajustado(precio_base, fecha_evento)
            enriched_prod = dict(p)
            enriched_prod["precio_unitario"] = precio
            enriched_prod["subtotal"] = precio * cantidad
            enriched_prod["nombre"] = p.get("catalogo_key", "") or p.get("nombre", "")
            # Agregar descripción del mobiliario de catálogo (para Word y detalle)
            mob_item = mob_by_id.get(p.get("mobiliario_id")) or mob_by_nombre.get(p.get("catalogo_key", ""))
            enriched_prod["descripcion"] = mob_item.descripcion if mob_item and mob_item.descripcion else p.get("descripcion", "")
            lug_dict["productos"].append(enriched_prod)
        enriched.append(lug_dict)
    return enriched
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
    """Devuelve el precio base redondeado, sin ajuste mensual.
    El ajuste de 3% por mes fue eliminado por petición del usuario.
    Se mantiene la firma para no romper los llamadores existentes.
    """
    return _redondear_precio(precio_base)


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
            # CASO 1: es un Juego (combo de varios mobiliarios)
            if prod.juego_id:
                juego = db.query(Juego).filter(Juego.id == prod.juego_id).first()
                if not juego or not juego.activo:
                    continue
                items_juego = db.query(JuegoItem).filter(JuegoItem.juego_id == juego.id).all()
                # Expandir visualmente cada item del juego para el PDF / detalle
                nombres_items = []
                cant_total_expandida = 0
                for ji in items_juego:
                    m = db.query(Mobiliario).filter(Mobiliario.id == ji.mobiliario_id).first()
                    if not m:
                        continue
                    cant = ji.cantidad * prod.cantidad
                    cant_total_expandida += cant
                    productos_calc.append(PresupuestoLinea(
                        mobiliario_id=ji.mobiliario_id,
                        nombre=m.nombre,
                        cantidad=cant,
                        precio_unitario=0.0,
                        subtotal=0.0,  # informativo; el subtotal real va en la línea resumen
                    ))
                # Precio del juego completo
                precio_base = prod.precio_manual if prod.precio_manual is not None else juego.precio_alquiler
                precio = calcular_precio_ajustado(precio_base, data.fecha_evento)
                sub = precio * prod.cantidad
                subtotal_lugar += sub
                # Línea resumen con el nombre del juego
                productos_calc.append(PresupuestoLinea(
                    mobiliario_id=0,
                    nombre=f"Juego: {juego.nombre}" + (f" ({cant_total_expandida} piezas)" if cant_total_expandida > 1 else ""),
                    cantidad=prod.cantidad,
                    precio_unitario=precio,
                    subtotal=sub,
                ))
                continue

            # CASO 2: Mobiliario individual
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
    # Enriquecer productos con precios calculados (mobiliario + juegos)
    # para que el Word y el frontend puedan mostrar precios sin recalcular.
    lugares_data = _enriquecer_productos_con_precios(lugares_data, db, p.fecha_evento)
    ppto_dict = {
        "nombre": getattr(p, 'nombre', '') or '',
        "cliente_nombre": p.cliente_nombre,
        "fecha_evento": p.fecha_evento,
        "tipo_evento": p.tipo_evento,
        "cantidad_invitados": p.cantidad_invitados,
        "localidad": p.localidad,
        "distancia_km": p.distancia_km,
        "subtotal_mobiliario": p.subtotal_mobiliario,
        "costo_logistica": p.costo_logistica,
        "costo_armado": getattr(p, 'costo_armado', None) or 0.0,
        "descuento": getattr(p, 'descuento', None) or 0.0,
        "total": p.total,
        "estado": p.estado,
    }
    return p, lugares_data, ppto_dict


def _lookup_mob_prices(db: Session) -> dict:
    all_mob = db.query(Mobiliario).filter(Mobiliario.activo == True).all()
    return {m.nombre: m.precio_alquiler for m in all_mob}


def _lookup_mob_fotos(db: Session) -> dict:
    """Retorna {nombre_mobiliario: ruta_absoluta_foto} para los que tienen foto.
    Usa la versión ORIGINAL (full/) si existe, sino cae back a la comprimida.
    Tolera que el directorio uploads/mobiliario no exista (otra PC sin fotos copiadas)."""
    from app.routers.mobiliario import _foto_full_path
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    upload_dir = os.path.join(project_root, "uploads", "mobiliario")
    if not os.path.isdir(upload_dir):
        return {}
    all_mob = db.query(Mobiliario).filter(Mobiliario.activo == True).all()
    fotos = {}
    for m in all_mob:
        if m.foto_path:
            foto_path = _foto_full_path(m.foto_path)
            if foto_path and os.path.exists(foto_path):
                fotos[m.nombre] = foto_path
    return fotos


@router.get("/{ppto_id}/pdf/completo")
def presupuesto_pdf_completo(ppto_id: int, db: Session = Depends(get_db)):
    try:
        p, lugares_raw, ppto = _get_ppto_with_lugares(ppto_id, db)
        mob_prices = _lookup_mob_prices(db)
        mob_fotos = _lookup_mob_fotos(db)
        from app.word_gen import generate_word_completo
        buf = generate_word_completo(ppto, lugares_raw, mob_prices, mob_fotos)
        return StreamingResponse(buf, media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                 headers={"Content-Disposition": f'attachment; filename="presupuesto_{ppto_id}_completo.docx"'})
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"Error generando Word: {str(e)}")


@router.get("/{ppto_id}/pdf/cliente")
def presupuesto_pdf_cliente(ppto_id: int, db: Session = Depends(get_db)):
    try:
        p, lugares_raw, ppto = _get_ppto_with_lugares(ppto_id, db)
        mob_fotos = _lookup_mob_fotos(db)
        from app.word_gen import generate_word_cliente
        buf = generate_word_cliente(ppto, lugares_raw, mob_fotos)
        return StreamingResponse(buf, media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                 headers={"Content-Disposition": f'attachment; filename="presupuesto_{ppto_id}_cliente.docx"'})
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"Error generando Word: {str(e)}")





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
    return [_presupuesto_to_out(p, db) for p in presupuestos]


@router.get("/{ppto_id}", response_model=PresupuestoDBOut)
def obtener_presupuesto(ppto_id: int, db: Session = Depends(get_db)):
    p = db.query(Presupuesto).filter(Presupuesto.id == ppto_id).first()
    if not p:
        raise HTTPException(404, "Presupuesto no encontrado")
    return _presupuesto_to_out(p, db)


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

    # DEBUG: log fecha recibida
    import logging
    # Enriquecer JSON de lugares con precios calculados (mobiliario + juegos)
    enriched_lugares = _enriquecer_productos_con_precios(data.lugares, db, data.fecha_evento)

    p = Presupuesto(
        nombre=data.nombre,
        cliente_id=cliente_id,
        cliente_nombre=cliente_nombre,
        fecha_evento=data.fecha_evento,
        tipo_evento=data.tipo_evento,
        cantidad_invitados=data.cantidad_invitados,
        localidad=data.localidad,
        distancia_km=data.distancia_km,
        lugares_json=json.dumps(enriched_lugares),
        subtotal_mobiliario=data.subtotal_mobiliario,
        costo_logistica=data.costo_logistica,
        costo_armado=data.costo_armado,
        descuento=data.descuento,
        total=data.total,
        whatsapp_text=data.whatsapp_text,
        estado=data.estado,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return _presupuesto_to_out(p, db)


@router.put("/{ppto_id}", response_model=PresupuestoDBOut)
def actualizar_presupuesto(ppto_id: int, data: PresupuestoSave, db: Session = Depends(get_db)):
    p = db.query(Presupuesto).filter(Presupuesto.id == ppto_id).first()
    if not p:
        raise HTTPException(404, "Presupuesto no encontrado")
    p.cliente_id = data.cliente_id
    p.nombre = data.nombre
    p.cliente_nombre = data.cliente_nombre
    p.fecha_evento = data.fecha_evento
    p.tipo_evento = data.tipo_evento
    p.cantidad_invitados = data.cantidad_invitados
    p.localidad = data.localidad
    p.distancia_km = data.distancia_km
    # Enriquecer JSON de lugares con precios calculados (mobiliario + juegos)
    enriched_lugares = _enriquecer_productos_con_precios(data.lugares, db, data.fecha_evento)
    p.lugares_json = json.dumps(enriched_lugares)
    p.subtotal_mobiliario = data.subtotal_mobiliario
    p.costo_logistica = data.costo_logistica
    p.costo_armado = data.costo_armado
    p.descuento = data.descuento
    p.total = data.total
    p.whatsapp_text = data.whatsapp_text
    p.estado = data.estado
    db.commit()
    db.refresh(p)
    return _presupuesto_to_out(p, db)


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

    from datetime import datetime as dt, date as _d
    # BUG FIX: parsear fecha sin timezone para evitar offset de 1 dia
    fecha = dt.now()
    if p.fecha_evento:
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d/%m/%y"):
            try:
                parsed = dt.strptime(p.fecha_evento.strip(), fmt)
                fecha = parsed
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
        costo_mano_obra=p.costo_armado or 0.0,
        monto_total=p.subtotal_mobiliario + p.costo_logistica + (p.costo_armado or 0) - (p.descuento or 0),
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
            # CASO JUEGO: crear una linea con el precio del combo
            jid = prod.get("juego_id")
            if jid:
                juego = db.query(Juego).filter(Juego.id == jid).first()
                if not juego:
                    continue
                # Usar el primer item del juego como mobiliario_id placeholder
                items_juego = db.query(JuegoItem).filter(JuegoItem.juego_id == juego.id).all()
                placeholder_mid = items_juego[0].mobiliario_id if items_juego else 1
                precio_juego = calcular_precio_ajustado(juego.precio_alquiler, p.fecha_evento)
                em = EventoMobiliario(
                    evento_id=evento.id,
                    mobiliario_id=placeholder_mid,
                    cantidad=prod.get("cantidad", 1),
                    precio_unitario=precio_juego,
                )
                db.add(em)
                continue

            # CASO MOBILIARIO INDIVIDUAL
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
    # Forzar que SQLAlchemy persista el monto_total recalculado
    db.flush()
    # Usar el total del presupuesto como monto_total del evento
    # (el presupuesto ya tiene los precios correctos incluyendo juegos)
    evento.monto_total = p.subtotal_mobiliario + p.costo_logistica + (p.costo_armado or 0) - (p.descuento or 0)

    p.evento_id = evento.id
    p.estado = "confirmado"
    db.commit()
    return {"ok": True, "evento_id": evento.id}


# ─── HELPERS ───
def _presupuesto_to_out(p: Presupuesto, db: Session = None) -> PresupuestoDBOut:
    lugares_data = json.loads(p.lugares_json) if p.lugares_json else []
    # Si los productos no tienen precio_unitario/subtotal (presupuestos viejos),
    # enriquecerlos calculando los precios con la fecha del evento.
    needs_enrich = False
    for lug in lugares_data:
        for prod in lug.get("productos", []):
            if "precio_unitario" not in prod or "subtotal" not in prod:
                needs_enrich = True
                break
        if needs_enrich:
            break
    if needs_enrich and db is not None:
        lugares_data = _enriquecer_productos_con_precios(lugares_data, db, p.fecha_evento)
    lugares = [LugarPresupuesto(**l) for l in lugares_data]
    return PresupuestoDBOut(
        id=p.id,
        nombre=getattr(p, 'nombre', '') or '',
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
        costo_armado=p.costo_armado or 0.0,
        descuento=getattr(p, 'descuento', 0.0) or 0.0,
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
