from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.database import get_db
from app.models import (
    Cliente, Evento, Mobiliario, EstadoEvento, EventoMobiliario,
    Presupuesto, SesionWhatsApp, LogisticaZona, LogisticaServicio, ConfigLogistica,
)
import os, json, re
from twilio.rest import Client

router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])

# ── Twilio ──
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN", "")
TWILIO_WHATSAPP_NUMBER = os.environ.get("TWILIO_WHATSAPP_NUMBER", "")

def get_twilio_client():
    if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
        return None
    return Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)


def _enviar_whatsapp(numero: str, texto: str):
    try:
        client = get_twilio_client()
        if not client:
            print("[WhatsApp] Twilio no configurado")
            return None
        if not numero.startswith("+"):
            numero = f"+54{numero}" if not numero.startswith("54") else f"+{numero}"
        from_number = f"whatsapp:{TWILIO_WHATSAPP_NUMBER}"
        to_number = f"whatsapp:{numero}"
        message = client.messages.create(body=texto, from_=from_number, to=to_number)
        print(f"[WhatsApp] Enviado a {numero}: {message.sid}")
        return {"sid": message.sid, "status": message.status}
    except Exception as e:
        print(f"[WhatsApp] Error enviando: {e}")
        return None


# ════════════════════════════════════════════════════════════════
# SESIONES — helpers
# ════════════════════════════════════════════════════════════════

def _get_sesion(numero: str, db: Session) -> SesionWhatsApp:
    s = db.query(SesionWhatsApp).filter(SesionWhatsApp.numero == numero).first()
    if not s:
        s = SesionWhatsApp(numero=numero, paso="inicio", datos="{}")
        db.add(s)
        db.commit()
        db.refresh(s)
    return s


def _set_paso(sesion: SesionWhatsApp, paso: str, db: Session, datos_extra: dict = None):
    sesion.paso = paso
    if datos_extra:
        d = json.loads(sesion.datos or "{}")
        d.update(datos_extra)
        sesion.datos = json.dumps(d)
    db.commit()


def _get_datos(sesion: SesionWhatsApp) -> dict:
    return json.loads(sesion.datos or "{}")


def _update_datos(sesion: SesionWhatsApp, clave: str, valor, db: Session):
    d = json.loads(sesion.datos or "{}")
    d[clave] = valor
    sesion.datos = json.dumps(d)
    db.commit()


# ════════════════════════════════════════════════════════════════
# FORMATEO DE PRECIOS
# ════════════════════════════════════════════════════════════════

def _fmt(val: float) -> str:
    return f"${int(round(val)):,}".replace(",", ".")


# ════════════════════════════════════════════════════════════════
# MOTOR CONVERSACIONAL — flujos por paso
# ════════════════════════════════════════════════════════════════

TIPOS_EVENTO = [
    "cumpleaños", "casamiento", "bautismo", "comunión", "comunion",
    "fiesta", "animación", "animacion", "corporativo", "agasajo",
    "quinceañera", "quince", "egresados", "baby shower",
]

def _es_tipo_evento(texto: str) -> bool:
    return any(t in texto for t in TIPOS_EVENTO)


def _parsear_fecha(texto: str):
    """Intenta parsear fecha en varios formatos argentinos."""
    texto = texto.strip()
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%d-%m-%y"):
        try:
            return datetime.strptime(texto, fmt).date()
        except ValueError:
            continue
    # "20 de julio" o "20 julio"
    m = re.match(r"(\d{1,2})\s+de?\s+(\w+)", texto, re.IGNORECASE)
    if m:
        meses = {
            "enero":1,"febrero":2,"marzo":3,"abril":4,"mayo":5,"junio":6,
            "julio":7,"agosto":8,"septiembre":9,"octubre":10,"noviembre":11,"diciembre":12
        }
        mes = meses.get(m.group(2).lower())
        if mes:
            try:
                return datetime(2026, mes, int(m.group(1))).date()
            except ValueError:
                pass
    return None


def _calcular_logistica(localidad: str, distancia_km: float = None, acarreo: bool = False, db: Session = None):
    """Calcula costo de logística basado en zona o km."""
    if distancia_km and distancia_km > 0 and db:
        cfg_km = db.query(ConfigLogistica).filter(ConfigLogistica.clave == "precio_por_km").first()
        precio_km = cfg_km.valor if cfg_km else 14000.0
        costo = distancia_km * precio_km
        if acarreo:
            cfg_ac = db.query(ConfigLogistica).filter(ConfigLogistica.clave == "acarreo_adicional").first()
            costo += cfg_ac.valor if cfg_ac else 3500.0
        return costo
    # Fallback a zonas
    zonas_cerca = ["Jáuregui", "Pueblo Nuevo"]
    if localidad in zonas_cerca:
        return 40000.0
    if db:
        zona = db.query(LogisticaZona).filter(LogisticaZona.nombre == localidad).first()
        if zona and zona.precio > 0:
            return zona.precio
    return 0.0


def _armar_presupuesto_texto(datos: dict, lugares_calc: list, subtotal: float, logistica: float, total: float) -> str:
    """Genera el texto de WhatsApp del presupuesto."""
    lines = [
        f"📋 *PRESUPUESTO — Azul Livings*",
        f"",
        f"👤 Cliente: {datos.get('nombre', '')}",
        f"🎉 Evento: {datos.get('tipo_evento', '')}",
        f"📅 Fecha: {datos.get('fecha', '')}",
        f"👥 Invitados: {datos.get('invitados', '-')}",
        f"📍 Localidad: {datos.get('localidad', 'Luján')}",
        f"",
    ]
    for lugar in lugares_calc:
        lines.append(f"▸ _{lugar['nombre']}_")
        for prod in lugar["productos"]:
            lines.append(f"  • {prod['nombre']} x{prod['cantidad']} — {_fmt(prod['subtotal'])}")
    lines.append(f"")
    lines.append(f"🪑 Mobiliario: {_fmt(subtotal)}")
    if logistica > 0:
        lines.append(f"🚚 Logística: {_fmt(logistica)}")
    lines.append(f"")
    lines.append(f"💰 *TOTAL: {_fmt(total)}*")
    lines.append(f"")
    lines.append(f"Seña del 50% para confirmar la reserva.")
    lines.append(f"Presupuesto válido por 7 días.")
    return "\n".join(lines)


# ─── PASOS DEL FLUJO ───

def _paso_inicio(numero, texto, db, sesion):
    """Punto de entrada. Detecta intención o saluda."""
    texto_limpio = texto.strip().lower()

    # Detectar intención rápida
    if texto_limpio in ("stock", "catálogo", "catalogo", "muebles"):
        return _responder_stock(db)

    if texto_limpio.startswith("disponible"):
        return _responder_disponible(texto_limpio, db)

    if texto_limpio in ("próximo", "proximo"):
        return _responder_proximo(db)

    if texto_limpio in ("eventos", "mis eventos"):
        return _responder_eventos(numero, db)

    if texto_limpio in ("contacto", "asesor", "humano"):
        return (
            "Dale, te paso con alguien del equipo 😊\n"
            "Mientras, si querés te puedo ayudar con un presupuesto rápido — solo decime *presupuesto*."
        )

    if texto_limpio == "presupuesto" or _es_tipo_evento(texto_limpio):
        # Iniciar flujo de presupuesto
        if _es_tipo_evento(texto_limpio):
            _update_datos(sesion, "tipo_evento", texto_limpio.title(), db)
        _set_paso(sesion, "pedir_nombre", db)
        # Ver si ya es cliente
        cliente = db.query(Cliente).filter(Cliente.whatsapp == numero).first()
        if cliente:
            _update_datos(sesion, "nombre", cliente.nombre, db)
            _update_datos(sesion, "cliente_id", cliente.id, db)
            if sesion.datos and json.loads(sesion.datos).get("tipo_evento"):
                _set_paso(sesion, "pedir_fecha", db)
                return (
                    f"¡{cliente.nombre}! Qué bueno que vuelvas 😊\n"
                    f"Vi que querés un presupuesto para un *{json.loads(sesion.datos)['tipo_evento']}*.\n"
                    f"¿Para qué fecha sería?"
                )
            else:
                _set_paso(sesion, "pedir_tipo", db)
                return f"¡{cliente.nombre}! Qué lindo verte de nuevo 😊\n¿Para qué tipo de evento querés el presupuesto?"

        if json.loads(sesion.datos).get("tipo_evento"):
            _set_paso(sesion, "pedir_nombre", db)
            return "¡Perfecto! Para armar el presupuesto, ¿cuál es tu nombre?"
        else:
            _set_paso(sesion, "pedir_nombre", db)
            return (
                "¡Hola! 👋 Te ayudo con el presupuesto.\n"
                "Primero, ¿cuál es tu nombre?"
            )

    # Saludo o no reconoce
    if texto_limpio.startswith(("hola", "buenas", "buen día", "buenas tardes", "buenas noches", "hi", "hello", "ey", "hey")):
        return (
            "¡Hola! Bienvenido a Azul Livings 🪑✨\n"
            "Te puedo ayudar con:\n\n"
            "• *presupuesto* — Te asesoro y armo una cotización\n"
            "• *stock* — Te muestro el catálogo\n"
            "• *disponible [fecha]* — Consulto disponibilidad\n"
            "• *eventos* — Veo tus próximos eventos\n"
            "• *contacto* — Te paso con alguien del equipo\n\n"
            "¿En qué te puedo ayudar?"
        )

    # No entendió — responder amable
    return (
        "Hmm, no estoy seguro de qué necesitás 🤔\n"
        "Podés escribirme:\n"
        "• *presupuesto* — para cotizar un evento\n"
        "• *stock* — para ver el catálogo\n"
        "• *contacto* —para hablar con alguien\n\n"
        "O simplemente decime qué estás buscando y veo cómo te ayudo 😊"
    )


def _paso_pedir_nombre(numero, texto, db, sesion):
    nombre = texto.strip().title()
    if len(nombre) < 2:
        return "¿Cómo dijiste? No entendí tu nombre 😅"

    _update_datos(sesion, "nombre", nombre, db)

    # Ver si ya existe como cliente por nombre
    cliente_existente = db.query(Cliente).filter(Cliente.nombre.ilike(f"%{nombre}%")).first()
    if cliente_existente:
        _update_datos(sesion, "cliente_id", cliente_existente.id, db)

    datos = _get_datos(sesion)
    if datos.get("tipo_evento"):
        _set_paso(sesion, "pedir_fecha", db)
        return f"¡Gracias, {nombre}! 👋\n¿Para qué fecha sería el *{datos['tipo_evento']}*?"
    else:
        _set_paso(sesion, "pedir_tipo", db)
        return f"¡Gracias, {nombre}! 👋\n¿Para qué tipo de evento es? (cumpleaños, casamiento, fiesta...)"


def _paso_pedir_tipo(numero, texto, db, sesion):
    tipo = texto.strip().title()
    if len(tipo) < 3:
        return "¿Qué tipo de evento es? Por ejemplo: cumpleaños, casamiento, bautismo..."

    _update_datos(sesion, "tipo_evento", tipo, db)
    _set_paso(sesion, "pedir_fecha", db)
    return f"¡{tipo}, qué lindo! 🎉\n¿Para qué fecha sería?"


def _paso_pedir_fecha(numero, texto, db, sesion):
    fecha = _parsear_fecha(texto)
    if not fecha:
        return (
            "No entendí la fecha 😅\n"
            "Decimela así: *15/07/2026* o *20 de julio*"
        )

    _update_datos(sesion, "fecha", fecha.strftime("%d/%m/%Y"), db)
    _set_paso(sesion, "pedir_invitados", db)
    return f"📅 Listo, {fecha.strftime('%d/%m/%Y')}.\n¿Cuántos invitados aproximadamente?"


def _paso_pedir_invitados(numero, texto, db, sesion):
    # Extraer número
    nums = re.findall(r"\d+", texto)
    if not nums:
        return "¿Cuántos invitados serían? Decime un número 😊"

    invitados = int(nums[0])
    _update_datos(sesion, "invitados", invitados, db)
    _set_paso(sesion, "pedir_localidad", db)
    return f"¡{invitados} invitados! 🥳\n¿En qué localidad sería el evento? (Luján, Jáuregui, Pilar...)"


def _paso_pedir_localidad(numero, texto, db, sesion):
    localidad = texto.strip().title()
    if len(localidad) < 2:
        return "¿En qué zona/localidad? Decime la ciudad o barrio 😊"

    _update_datos(sesion, "localidad", localidad, db)

    # Ver si necesita acarreo adicional
    _set_paso(sesion, "pedir_acarreo", db)
    return (
        f"📍 {localidad}, anotado.\n"
        f"¿Necesitás acarreo adicional? ( escaleras, pisos altos, sin ascensor )\n"
        f"Respondé *sí* o *no*"
    )


def _paso_pedir_acarreo(numero, texto, db, sesion):
    texto_l = texto.strip().lower()
    acarreo = texto_l in ("sí", "si", "sip", "siempre", "dale", "yes", "s")

    _update_datos(sesion, "acarreo_adicional", acarreo, db)
    _set_paso(sesion, "pedir_items", db)

    # Mostrar categorías para elegir
    categorias = db.query(Mobiliario.categoria).filter(Mobiliario.activo == True).distinct().all()
    cats = [c[0] for c in categorias]

    resp = "Ahora lo divertido: ¿qué mobiliario necesitás? 🪑\n\n"
    resp += "Podes escribir lo que quieras, por ejemplo:\n"
    resp += "• *sillas* — Te muestro las sillas\n"
    resp += "• *mesas* — Te muestro las mesas\n"
    resp += "• *Quiero 50 sillas paris y 6 mesas redondas*\n\n"
    resp += "Categorías disponibles:\n"
    for c in cats:
        resp += f"  • *{c.lower()}*\n"
    resp += "\nCuando termines de agregar items, escribí *listo*"

    return resp


def _paso_pedir_items(numero, texto, db, sesion):
    texto_l = texto.strip().lower()

    if texto_l in ("listo", "eso es todo", "terminé", "termine", "basta", "ya está", "ya esta", "confirmar"):
        return _armar_resumen(numero, db, sesion)

    # Si escribe una categoría → mostrar items
    categorias = db.query(Mobiliario.categoria).filter(Mobiliario.activo == True).distinct().all()
    cats_lower = {c[0].lower(): c[0] for c in categorias}

    if texto_l in cats_lower:
        cat_real = cats_lower[texto_l]
        items = db.query(Mobiliario).filter(
            Mobiliario.activo == True,
            Mobiliario.categoria == cat_real
        ).limit(15).all()
        if items:
            resp = f"🪑 *{cat_real} disponibles:*\n\n"
            for i in items:
                resp += f"• {i.nombre} — {_fmt(i.precio_alquiler)}\n"
            resp += "\nDecime qué querés y cuántos. Ej: *10 sillas paris*"
            return resp
        else:
            return f"No tengo items en {texto_l} ahora 😕 Probá con otra categoría."

    # Intentar parsear items: "10 sillas paris" o "sillas paris 10" o "quiero 50 sillas"
    items_actuales = _get_datos(sesion).get("items", [])
    parsed = _parsear_items_texto(texto, db)

    if parsed:
        for item in parsed:
            items_actuales.append(item)
        _update_datos(sesion, "items", items_actuales, db)

        resumen_items = ""
        for it in items_actuales:
            resumen_items += f"  • {it['cantidad']}x {it['nombre']} — {_fmt(it['subtotal'])}\n"

        return (
            f"✅ Anotado!\n\n"
            f"Tu lista hasta ahora:\n{resumen_items}\n"
            f"Seguí agregando o decí *listo* para ver el presupuesto completo."
        )

    # No reconoció nada
    return (
        "No estoy seguro de qué querés 🤔\n"
        "Probá escribir algo como:\n"
        "• *10 sillas París*\n"
        "• *mesas redondas*\n"
        "• *sillones* (para ver opciones)\n\n"
        "O decí *listo* si ya tenés todo."
    )


def _parsear_items_texto(texto: str, db: Session) -> list:
    """Parsea texto para extraer items de mobiliario.
    Retorna lista de dicts: [{mobiliario_id, nombre, cantidad, precio_unitario, subtotal}]
    """
    all_mob = db.query(Mobiliario).filter(Mobiliario.activo == True).all()
    mob_by_nombre = {m.nombre.lower(): m for m in all_mob}
    mob_by_nombre_partial = {}
    for m in all_mob:
        # Mapear por palabras clave del nombre
        palabras = m.nombre.lower().split()
        for p in palabras:
            if len(p) > 3:
                mob_by_nombre_partial[p] = m

    resultado = []
    # Intentar varios patrones
    # Patrón 1: "10 sillas paris" o "5 mesas redondas"
    match = re.match(r"(\d+)\s+(.+)", texto.strip().lower())
    if match:
        cantidad = int(match.group(1))
        nombre_busq = match.group(2).strip()
        mob = mob_by_nombre.get(nombre_busq)
        if not mob:
            # Buscar parcial
            for key, m in mob_by_nombre_partial.items():
                if key in nombre_busq or nombre_busq in key:
                    mob = m
                    break
            # Buscar por contains
            if not mob:
                for m in all_mob:
                    if nombre_busq in m.nombre.lower() or m.nombre.lower() in nombre_busq:
                        mob = m
                        break
        if mob:
            resultado.append({
                "mobiliario_id": mob.id,
                "nombre": mob.nombre,
                "cantidad": cantidad,
                "precio_unitario": mob.precio_alquiler,
                "subtotal": mob.precio_alquiler * cantidad,
            })
            return resultado

    # Patrón 2: "sillas paris 10" (nombre primero)
    match = re.match(r"(.+?)\s+(\d+)$", texto.strip().lower())
    if match:
        nombre_busq = match.group(1).strip()
        cantidad = int(match.group(2))
        mob = None
        for m in all_mob:
            if nombre_busq in m.nombre.lower() or m.nombre.lower() in nombre_busq:
                mob = m
                break
        if mob:
            resultado.append({
                "mobiliario_id": mob.id,
                "nombre": mob.nombre,
                "cantidad": cantidad,
                "precio_unitario": mob.precio_alquiler,
                "subtotal": mob.precio_alquiler * cantidad,
            })
            return resultado

    # Patrón 3: solo nombre sin cantidad ("sillas paris") → muestra opciones
    nombre_busq = texto.strip().lower()
    matches = [m for m in all_mob if nombre_busq in m.nombre.lower()]
    if len(matches) == 1:
        mob = matches[0]
        resultado.append({
            "mobiliario_id": mob.id,
            "nombre": mob.nombre,
            "cantidad": 1,
            "precio_unitario": mob.precio_alquiler,
            "subtotal": mob.precio_alquiler,
        })
        return resultado
    elif len(matches) > 1:
        # Múltiples, no agregar — que elija
        return []

    # Patrón 4: keyword search
    palabras = texto.strip().lower().split()
    for p in palabras:
        if len(p) > 3 and p in mob_by_nombre_partial:
            mob = mob_by_nombre_partial[p]
            resultado.append({
                "mobiliario_id": mob.id,
                "nombre": mob.nombre,
                "cantidad": 1,
                "precio_unitario": mob.precio_alquiler,
                "subtotal": mob.precio_alquiler,
            })
            return resultado

    return resultado


def _armar_resumen(numero, db, sesion):
    """Arma el resumen del presupuesto y lo muestra para confirmar."""
    datos = _get_datos(sesion)
    items = datos.get("items", [])

    if not items:
        _set_paso(sesion, "pedir_items", db)
        return (
            "¡No agregaste nada todavía! 😅\n"
            "Decime qué mobiliario necesitás. Ej: *10 sillas París*\n"
            "O el nombre de una categoría para ver opciones: *sillas*, *mesas*, etc."
        )

    # Calcular subtotal mobiliario
    subtotal_mob = sum(it["subtotal"] for it in items)

    # Calcular logística
    localidad = datos.get("localidad", "Luján")
    acarreo = datos.get("acarreo_adicional", False)
    costo_logistica = _calcular_logistica(localidad, acarreo=acarreo, db=db)

    total = subtotal_mob + costo_logistica

    # Guardar cálculos
    _update_datos(sesion, "subtotal_mobiliario", subtotal_mob, db)
    _update_datos(sesion, "costo_logistica", costo_logistica, db)
    _update_datos(sesion, "total", total, db)

    # Armar texto
    nombre = datos.get("nombre", "")
    tipo = datos.get("tipo_evento", "")
    fecha = datos.get("fecha", "")
    invitados = datos.get("invitados", "-")

    resp = "📋 *Tu presupuesto:*\n\n"
    resp += f"👤 {nombre}\n"
    resp += f"🎉 {tipo}\n"
    resp += f"📅 {fecha}\n"
    resp += f"👥 {invitados} invitados\n"
    resp += f"📍 {localidad}\n\n"
    resp += "🪑 *Mobiliario:*\n"
    for it in items:
        resp += f"  • {it['cantidad']}x {it['nombre']} — {_fmt(it['subtotal'])}\n"
    resp += f"\n  Subtotal: {_fmt(subtotal_mob)}\n"
    if costo_logistica > 0:
        resp += f"🚚 Logística: {_fmt(costo_logistica)}\n"
        if acarreo:
            resp += "  (incluye acarreo adicional)\n"
    resp += f"\n💰 *TOTAL: {_fmt(total)}*\n\n"
    resp += "¿Todo bien? Respondé:\n"
    resp += "• *confirmar* — Guardo el presupuesto\n"
    resp += "• *cambiar* — Si querés modificar algo\n"
    resp += "• *agregar* — Para sumar más items"

    _set_paso(sesion, "confirmar_presupuesto", db)
    return resp


def _paso_confirmar(numero, texto, db, sesion):
    texto_l = texto.strip().lower()

    if texto_l in ("confirmar", "confirmo", "dale", "sí", "si", "ok", "perfecto", "buenísimo", "genial"):
        return _guardar_presupuesto_y_cliente(numero, db, sesion)

    if texto_l in ("cambiar", "modificar", "cambio"):
        _set_paso(sesion, "pedir_items", db)
        datos = _get_datos(sesion)
        items = datos.get("items", [])
        if items:
            resp = "¿Qué querés cambiar?\n\nTu lista actual:\n"
            for i, it in enumerate(items):
                resp += f"  {i+1}. {it['cantidad']}x {it['nombre']} — {_fmt(it['subtotal'])}\n"
            resp += "\nPara sacar un item decí *sacar 1* (el número).\nPara agregar decí *agregar*.\nO decí *listo* cuando termines."
            return resp
        else:
            return "Tu lista está vacía. Agregá lo que necesites y decí *listo*."

    if texto_l in ("agregar", "sumar", "más", "mas"):
        _set_paso(sesion, "pedir_items", db)
        datos = _get_datos(sesion)
        items = datos.get("items", [])
        resp = "Dale, ¿qué querés agregar? 🪑\n\nHasta ahora tenés:\n"
        for it in items:
            resp += f"  • {it['cantidad']}x {it['nombre']}\n"
        resp += "\nDecime el item y la cantidad, o *listo* para terminar."
        return resp

    if texto_l.startswith("sacar"):
        datos = _get_datos(sesion)
        items = datos.get("items", [])
        nums = re.findall(r"\d+", texto_l)
        if nums:
            idx = int(nums[0]) - 1
            if 0 <= idx < len(items):
                removed = items.pop(idx)
                _update_datos(sesion, "items", items, db)
                resp = f"✅ Saqué {removed['cantidad']}x {removed['nombre']}.\n\nQuedan:\n"
                for i, it in enumerate(items):
                    resp += f"  {i+1}. {it['cantidad']}x {it['nombre']}\n"
                resp += "\nDecí *listo* para ver el presupuesto actualizado."
                return resp
        return "Decime el número del item que querés sacar. Ej: *sacar 1*"

    return (
        "¿Qué hacemos? 😊\n"
        "• *confirmar* — Guardo el presupuesto\n"
        "• *cambiar* — Modificás algo\n"
        "• *agregar* — Sumás items\n"
        "• *cancelar* — Cancelás todo"
    )


def _guardar_presupuesto_y_cliente(numero, db, sesion):
    """Crea el cliente y presupuesto en la DB."""
    datos = _get_datos(sesion)

    # ── Crear/actualizar cliente ──
    cliente_id = datos.get("cliente_id")
    cliente = None
    if cliente_id:
        cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()

    if not cliente:
        # Buscar por WhatsApp
        cliente = db.query(Cliente).filter(Cliente.whatsapp == numero).first()

    if not cliente:
        # Crear nuevo
        # Limpiar número para almacenar
        wa_num = numero.lstrip("+")
        cliente = Cliente(
            nombre=datos.get("nombre", "Sin nombre"),
            whatsapp=wa_num,
            telefono=wa_num,
            notas=f"Creado vía bot WhatsApp — {datos.get('tipo_evento', '')}",
        )
        db.add(cliente)
        db.commit()
        db.refresh(cliente)
        print(f"[Bot] Nuevo cliente creado: {cliente.nombre} (ID {cliente.id})")

    # ── Armar lugares para presupuesto ──
    items = datos.get("items", [])
    productos = []
    for it in items:
        productos.append({
            "catalogo_key": it["nombre"],
            "mobiliario_id": it["mobiliario_id"],
            "cantidad": it["cantidad"],
            "precio_manual": it["precio_unitario"],
            "notas": "",
        })

    lugares_json = json.dumps([{"nombre": "General", "productos": productos}])

    subtotal_mob = datos.get("subtotal_mobiliario", sum(it["subtotal"] for it in items))
    costo_log = datos.get("costo_logistica", 0)
    total = datos.get("total", subtotal_mob + costo_log)

    # ── Generar texto WhatsApp ──
    wa_text = _armar_presupuesto_texto(
        datos,
        [{"nombre": "General", "productos": items}],
        subtotal_mob, costo_log, total,
    )

    # ── Crear presupuesto ──
    presupuesto = Presupuesto(
        cliente_id=cliente.id,
        cliente_nombre=cliente.nombre,
        fecha_evento=datos.get("fecha", ""),
        tipo_evento=datos.get("tipo_evento", ""),
        cantidad_invitados=datos.get("invitados"),
        localidad=datos.get("localidad", "Luján"),
        distancia_km=None,
        logistica_tipo="Traslado Simple",
        acarreo_adicional=datos.get("acarreo_adicional", False),
        solo_ambientacion=False,
        lugares_json=lugares_json,
        subtotal_mobiliario=subtotal_mob,
        costo_logistica=costo_log,
        total=total,
        whatsapp_text=wa_text,
        estado="borrador",
    )
    db.add(presupuesto)
    db.commit()
    db.refresh(presupuesto)
    print(f"[Bot] Presupuesto creado: #{presupuesto.id} — Total: {total}")

    # ── Actualizar sesión ──
    sesion.cliente_id = cliente.id
    sesion.presupuesto_id = presupuesto.id
    _set_paso(sesion, "inicio", db)
    # Limpiar datos de sesión para la próxima
    sesion.datos = json.dumps({
        "ultimo_presupuesto": presupuesto.id,
        "ultimo_cliente": cliente.id,
    })
    db.commit()

    return (
        f"✅ ¡Listo! Tu presupuesto #{presupuesto.id} quedó guardado.\n\n"
        f"💰 *Total: {_fmt(total)}*\n\n"
        f"Te lo paso en forma de resumen:\n\n"
        f"{wa_text}\n\n"
        f"Si querés confirmar la reserva, hablá con nosotros que te explicamos todo 😊\n"
        f"¿Algo más en lo que te pueda ayudar?"
    )


# ─── Comandos de info (disponibles siempre) ───

def _responder_stock(db: Session) -> str:
    categorias = db.query(Mobiliario.categoria).filter(Mobiliario.activo == True).distinct().all()
    if not categorias:
        return "No tengo mobiliario cargado en este momento 😕"

    resp = "📦 *Catálogo de Azul Livings:*\n\n"
    for cat in categorias:
        count = db.query(Mobiliario).filter(Mobiliario.activo == True, Mobiliario.categoria == cat[0]).count()
        resp += f"• *{cat[0]}* — {count} items\n"
    resp += "\nEscribí el nombre de una categoría para ver los detalles.\nEj: *sillas*, *mesas*"
    return resp


def _responder_disponible(texto: str, db: Session) -> str:
    partes = texto.split()
    if len(partes) < 2:
        return "Usá: *disponible DD/MM/AAAA*\nEjemplo: *disponible 20/07/2026*"

    fecha = _parsear_fecha(" ".join(partes[1:]))
    if not fecha:
        return "No entendí la fecha 😅 Usá: *disponible 20/07/2026*"

    eventos = db.query(Evento).filter(
        Evento.estado.in_([EstadoEvento.reserva, EstadoEvento.confirmado]),
    ).all()
    eventos_fecha = [ev for ev in eventos if ev.fecha.date() == fecha or (ev.fecha_fin and ev.fecha.date() <= fecha <= ev.fecha_fin.date())]

    comprometido = {}
    for ev in eventos_fecha:
        items = db.query(EventoMobiliario).filter(EventoMobiliario.evento_id == ev.id).all()
        for item in items:
            comprometido[item.mobiliario_id] = comprometido.get(item.mobiliario_id, 0) + item.cantidad

    mobiliario = db.query(Mobiliario).filter(Mobiliario.activo == True).all()
    disponible = []
    for m in mobiliario:
        stock_disp = m.stock_total - comprometido.get(m.id, 0)
        if stock_disp > 0:
            disponible.append({"nombre": m.nombre, "disponible": stock_disp, "precio": m.precio_alquiler})

    if disponible:
        resp = f"📅 *Disponible para {fecha.strftime('%d/%m/%Y')}:*\n\n"
        for item in disponible[:10]:
            resp += f"• {item['nombre']} — {item['disponible']} u. ({_fmt(item['precio'])})\n"
        if len(disponible) > 10:
            resp += f"\n(y {len(disponible)-10} más...)"
        return resp
    else:
        return f"No hay mobiliario disponible para el {fecha.strftime('%d/%m/%Y')} 😔"


def _responder_proximo(db: Session) -> str:
    hoy = datetime.now()
    evento = db.query(Evento).filter(
        Evento.estado.in_([EstadoEvento.reserva, EstadoEvento.confirmado]),
        Evento.fecha >= hoy,
    ).order_by(Evento.fecha).first()
    if evento:
        cliente = db.query(Cliente).filter(Cliente.id == evento.cliente_id).first()
        return (
            f"📅 El próximo evento es:\n"
            f"*{evento.titulo}*\n"
            f"📆 {evento.fecha.strftime('%d/%m/%Y')}\n"
            f"📍 {evento.lugar or 'Sin especificar'}\n"
            f"👤 {cliente.nombre if cliente else '-'}"
        )
    return "No hay eventos próximos por ahora."


def _responder_eventos(numero: str, db: Session) -> str:
    cliente = db.query(Cliente).filter(Cliente.whatsapp == numero).first()
    if not cliente:
        return "No te tengo registrado aún 😊 Si querés, pedí un *presupuesto* y te registro."

    eventos = db.query(Evento).filter(
        Evento.cliente_id == cliente.id,
        Evento.fecha >= datetime.now(),
    ).order_by(Evento.fecha).limit(5).all()

    if not eventos:
        return f"No tenés eventos próximos agendados, {cliente.nombre}."

    resp = f"📋 *Tus eventos, {cliente.nombre}:*\n\n"
    for e in eventos:
        resp += f"• {e.titulo} — {e.fecha.strftime('%d/%m')}\n"
    return resp


# ════════════════════════════════════════════════════════════════
# PASO → FUNCIÓN (dispatch table)
# ════════════════════════════════════════════════════════════════

PASOS = {
    "inicio": _paso_inicio,
    "pedir_nombre": _paso_pedir_nombre,
    "pedir_tipo": _paso_pedir_tipo,
    "pedir_fecha": _paso_pedir_fecha,
    "pedir_invitados": _paso_pedir_invitados,
    "pedir_localidad": _paso_pedir_localidad,
    "pedir_acarreo": _paso_pedir_acarreo,
    "pedir_items": _paso_pedir_items,
    "confirmar_presupuesto": _paso_confirmar,
}

# Comandos rápidos que resetean sesión
COMANDOS_RAPIDOS = {"stock", "próximo", "proximo", "eventos", "contacto", "asesor", "humano", "catálogo", "catalogo", "muebles"}


# ════════════════════════════════════════════════════════════════
# WEBHOOK — punto de entrada Twilio
# ════════════════════════════════════════════════════════════════

@router.post("/webhook")
async def webhook_whatsapp(request: Request, db: Session = Depends(get_db)):
    form_data = await request.form()

    try:
        from_number = form_data.get("From", "").replace("whatsapp:", "")
        body = form_data.get("Body", "")

        if not body:
            return PlainTextResponse("")

        numero = from_number.lstrip("+")
        texto = body.strip()
        texto_l = texto.lower()

        print(f"📨 [{datetime.now().strftime('%H:%M:%S')}] {numero}: {texto}")

        # Obtener o crear sesión
        sesion = _get_sesion(numero, db)
        paso_actual = sesion.paso

        # Si está en medio de un flujo y escribe un comando rápido → resetear
        if paso_actual != "inicio" and texto_l in COMANDOS_RAPIDOS:
            _set_paso(sesion, "inicio", db)
            paso_actual = "inicio"

        # Si escribe "cancelar" en cualquier momento → resetear
        if texto_l in ("cancelar", "cancel", "volver", "volver al inicio", "menu", "menú"):
            _set_paso(sesion, "inicio", db)
            resp = (
                "Cancelado. Volvemos a empezar 😊\n\n"
                "¿En qué te puedo ayudar?\n"
                "• *presupuesto*\n• *stock*\n• *contacto*"
            )
            _enviar_whatsapp(numero, resp)
            return PlainTextResponse("")

        # Dispatch al paso correspondiente
        handler = PASOS.get(paso_actual, _paso_inicio)
        respuesta = handler(numero, texto, db, sesion)

        # Enviar respuesta
        _enviar_whatsapp(numero, respuesta)

    except Exception as e:
        print(f"[WhatsApp Webhook] Error: {e}")
        import traceback
        traceback.print_exc()

    return PlainTextResponse("")


# ════════════════════════════════════════════════════════════════
# ENDPOINTS ADMIN / DEBUG
# ════════════════════════════════════════════════════════════════

@router.get("/admin/config")
def get_config(db: Session = Depends(get_db)):
    from app.models import ConfiguracionWhatsApp
    configs = db.query(ConfiguracionWhatsApp).all()
    return {c.clave: c.valor for c in configs}


@router.get("/admin/sesiones")
def get_sesiones(db: Session = Depends(get_db)):
    """Ver sesiones activas del bot."""
    sesiones = db.query(SesionWhatsApp).order_by(SesionWhatsApp.updated_at.desc()).limit(50).all()
    return [{
        "numero": s.numero,
        "paso": s.paso,
        "datos": json.loads(s.datos or "{}"),
        "cliente_id": s.cliente_id,
        "presupuesto_id": s.presupuesto_id,
        "updated_at": str(s.updated_at) if s.updated_at else None,
    } for s in sesiones]


@router.post("/admin/sesion/{numero}/reset")
def reset_sesion(numero: str, db: Session = Depends(get_db)):
    """Resetea la sesión de un número."""
    s = db.query(SesionWhatsApp).filter(SesionWhatsApp.numero == numero).first()
    if s:
        s.paso = "inicio"
        s.datos = "{}"
        db.commit()
    return {"ok": True, "msg": f"Sesión de {numero} reseteada"}


@router.get("/enviar/{numero}")
def enviar_texto(numero: str, texto: str):
    resultado = _enviar_whatsapp(numero, texto)
    if resultado:
        return {"ok": True, "sid": resultado["sid"]}
    return {"ok": False, "error": "No se pudo enviar"}


@router.get("/test")
def test_twilio():
    client = get_twilio_client()
    if not client:
        return {"error": "Twilio no configurado"}
    try:
        account = client.api.accounts(TWILIO_ACCOUNT_SID).fetch()
        return {"ok": True, "account": account.friendly_name, "status": account.status}
    except Exception as e:
        return {"error": str(e)}
