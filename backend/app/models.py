from sqlalchemy import Column, Integer, String, Float, Text, DateTime, Boolean, ForeignKey, Enum
from sqlalchemy.sql import func
from app.database import Base
import enum


class EstadoEvento(str, enum.Enum):
    reserva = "reserva"
    confirmado = "confirmado"
    cancelado = "cancelado"
    completado = "completado"


class EstadoPago(str, enum.Enum):
    pendiente = "pendiente"
    senia = "seña"
    pagado = "pagado"
    parcial = "parcial"


# ─── Mobiliario ───
class Mobiliario(Base):
    __tablename__ = "mobiliario"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(150), nullable=False)
    categoria = Column(String(100), nullable=False)  # silla, sillón, mesa, almohada, candelabro, etc.
    descripcion = Column(Text, default="")
    precio_alquiler = Column(Float, nullable=False)  # precio por evento
    stock_total = Column(Integer, nullable=False, default=1)
    foto_path = Column(String(500), default="")  # ruta relativa al archivo subido
    activo = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())


# ─── Cliente ───
class Cliente(Base):
    __tablename__ = "cliente"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(200), nullable=False)
    telefono = Column(String(50), default="")
    email = Column(String(200), default="")
    whatsapp = Column(String(50), default="")
    notas = Column(Text, default="")
    created_at = Column(DateTime, server_default=func.now())


# ─── Evento ───
class Evento(Base):
    __tablename__ = "evento"

    id = Column(Integer, primary_key=True, index=True)
    cliente_id = Column(Integer, ForeignKey("cliente.id"), nullable=False)
    titulo = Column(String(200), nullable=False)
    fecha = Column(DateTime, nullable=False)
    fecha_fin = Column(DateTime, nullable=True)
    lugar = Column(String(300), default="")
    estado = Column(Enum(EstadoEvento), default=EstadoEvento.reserva)
    estado_pago = Column(Enum(EstadoPago), default=EstadoPago.pendiente)
    monto_total = Column(Float, default=0.0)
    monto_senia = Column(Float, default=0.0)
    costo_traslado = Column(Float, default=0.0)
    costo_mano_obra = Column(Float, default=0.0)
    notas = Column(Text, default="")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())


# ─── EventoMobiliario (many-to-many) ───
class EventoMobiliario(Base):
    __tablename__ = "evento_mobiliario"

    id = Column(Integer, primary_key=True, index=True)
    evento_id = Column(Integer, ForeignKey("evento.id"), nullable=False)
    mobiliario_id = Column(Integer, ForeignKey("mobiliario.id"), nullable=False)
    cantidad = Column(Integer, nullable=False, default=1)
    precio_unitario = Column(Float, nullable=False)  # snapshot del precio al momento del presupuesto


# ─── Logística (zonas de entrega y servicios) ───
class LogisticaZona(Base):
    __tablename__ = "logistica_zona"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False, unique=True)
    precio = Column(Float, nullable=False, default=0.0)


class LogisticaServicio(Base):
    __tablename__ = "logistica_servicio"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False, unique=True)
    precio = Column(Float, nullable=False, default=0.0)


class ConfigLogistica(Base):
    __tablename__ = "config_logistica"

    id = Column(Integer, primary_key=True, index=True)
    clave = Column(String(100), nullable=False, unique=True)
    valor = Column(Float, nullable=False, default=0.0)


# ─── Presupuesto guardado ───
class Presupuesto(Base):
    __tablename__ = "presupuesto"

    id = Column(Integer, primary_key=True, index=True)
    cliente_id = Column(Integer, ForeignKey("cliente.id"), nullable=True)
    cliente_nombre = Column(String(200), default="")
    fecha_evento = Column(String(100), default="")
    tipo_evento = Column(String(100), default="")
    cantidad_invitados = Column(Integer, nullable=True)
    localidad = Column(String(100), default="Luján")
    distancia_km = Column(Integer, nullable=True)
    # DEPRECATED: estas columnas se mantienen por compatibilidad con datos
    # existentes, pero ya no se usan en los cálculos de logística nuevos.
    logistica_tipo = Column(String(100), default="Traslado Simple")
    acarreo_adicional = Column(Boolean, default=False)
    solo_ambientacion = Column(Boolean, default=False)
    lugares_json = Column(Text, default="[]")  # JSON serializado: [{nombre, productos}]
    subtotal_mobiliario = Column(Float, default=0.0)
    costo_logistica = Column(Float, default=0.0)
    total = Column(Float, default=0.0)
    whatsapp_text = Column(Text, default="")
    estado = Column(String(30), default="borrador")  # borrador, enviado, confirmado, cancelado
    evento_id = Column(Integer, ForeignKey("evento.id"), nullable=True)  # si se convirtió en evento
    created_at = Column(DateTime, server_default=func.now())


# ─── Registro financiero ───
class RegistroFinanciero(Base):
    __tablename__ = "registro_financiero"

    id = Column(Integer, primary_key=True, index=True)
    evento_id = Column(Integer, ForeignKey("evento.id"), nullable=True)
    presupuesto_id = Column(Integer, ForeignKey("presupuesto.id"), nullable=True)
    tipo = Column(String(50), nullable=False)  # ingreso, egreso
    concepto = Column(String(300), nullable=False)
    monto = Column(Float, nullable=False)
    fecha = Column(DateTime, server_default=func.now())
    notas = Column(Text, default="")


# ─── Sesión de conversación WhatsApp ───
class SesionWhatsApp(Base):
    __tablename__ = "sesion_whatsapp"

    id = Column(Integer, primary_key=True, index=True)
    numero = Column(String(50), unique=True, nullable=False, index=True)
    paso = Column(String(80), default="inicio")  # paso actual del flujo
    datos = Column(Text, default="{}")  # JSON temporal: nombre, tipo_evento, fecha, invitados, localidad, items, etc.
    cliente_id = Column(Integer, ForeignKey("cliente.id"), nullable=True)
    presupuesto_id = Column(Integer, ForeignKey("presupuesto.id"), nullable=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


# ─── Configuracion WhatsApp ───
class ConfiguracionWhatsApp(Base):
    __tablename__ = "configuracion_whatsapp"

    id = Column(Integer, primary_key=True, index=True)
    clave = Column(String(100), unique=True, nullable=False)
    valor = Column(Text, default="")
    descripcion = Column(String(300), default="")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
