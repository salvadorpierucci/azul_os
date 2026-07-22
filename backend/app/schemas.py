from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime


# ─── Mobiliario ───
class MobiliarioBase(BaseModel):
    nombre: str
    categoria: str
    descripcion: Optional[str] = ""
    precio_alquiler: float
    stock_total: int = 1
    foto_path: Optional[str] = ""
    activo: bool = True


class MobiliarioCreate(MobiliarioBase):
    pass


class MobiliarioOut(MobiliarioBase):
    id: int
    stock_disponible: int = 0  # calculado dinámicamente

    class Config:
        from_attributes = True


# ─── Juego (combo de N unidades de un mobiliario) ───
class JuegoSave(BaseModel):
    nombre: str
    mobiliario_id: int
    cantidad: int = 1
    precio_alquiler: float = 0.0
    descripcion: Optional[str] = ""
    activo: bool = True

class JuegoOut(JuegoSave):
    id: int
    mobiliario_nombre: str = ""
    mobiliario_stock: int = 0
    class Config:
        from_attributes = True

class JuegoUpdate(BaseModel):
    nombre: Optional[str] = None
    mobiliario_id: Optional[int] = None
    cantidad: Optional[int] = None
    precio_alquiler: Optional[float] = None
    descripcion: Optional[str] = None
    activo: Optional[bool] = None


# ─── Cliente ───
class ClienteBase(BaseModel):
    nombre: str
    telefono: Optional[str] = ""
    email: Optional[str] = ""
    whatsapp: Optional[str] = ""
    notas: Optional[str] = ""


class ClienteCreate(ClienteBase):
    pass


class ClienteUpdate(BaseModel):
    nombre: Optional[str] = None
    telefono: Optional[str] = None
    email: Optional[str] = None
    whatsapp: Optional[str] = None
    notas: Optional[str] = None


class ClienteOut(ClienteBase):
    id: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ─── Evento ───
class EventoBase(BaseModel):
    cliente_id: int
    titulo: str
    fecha: datetime
    fecha_fin: Optional[datetime] = None
    lugar: Optional[str] = ""
    estado: Optional[str] = "reserva"
    estado_pago: Optional[str] = "pendiente"
    costo_traslado: Optional[float] = 0.0
    costo_mano_obra: Optional[float] = 0.0
    notas: Optional[str] = ""


class EventoCreate(EventoBase):
    pass


class EventoUpdate(BaseModel):
    """Partial update — solo los campos enviados se modifican"""
    cliente_id: Optional[int] = None
    titulo: Optional[str] = None
    fecha: Optional[datetime] = None
    fecha_fin: Optional[datetime] = None
    lugar: Optional[str] = None
    estado: Optional[str] = None
    estado_pago: Optional[str] = None
    costo_traslado: Optional[float] = None
    costo_mano_obra: Optional[float] = None
    monto_senia: Optional[float] = None
    notas: Optional[str] = None


class EventoOut(EventoBase):
    id: int
    monto_total: float = 0.0
    monto_senia: float = 0.0
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class EventoMobiliarioItem(BaseModel):
    id: int
    mobiliario_id: int
    nombre: str
    categoria: str = ""
    cantidad: int
    precio_unitario: float
    subtotal: float


class EventoDetalleOut(BaseModel):
    id: int
    cliente_id: int
    cliente_nombre: str = ""
    titulo: str
    fecha: datetime
    fecha_fin: Optional[datetime] = None
    lugar: Optional[str] = ""
    estado: Optional[str] = "reserva"
    estado_pago: Optional[str] = "pendiente"
    costo_traslado: float = 0.0
    costo_mano_obra: float = 0.0
    monto_total: float = 0.0
    monto_senia: float = 0.0
    notas: Optional[str] = ""
    created_at: Optional[datetime] = None
    items: List[EventoMobiliarioItem] = []


# ─── EventoMobiliario ───
class EventoMobiliarioBase(BaseModel):
    mobiliario_id: int
    cantidad: int = 1


class EventoMobiliarioCreate(EventoMobiliarioBase):
    pass


class EventoMobiliarioOut(EventoMobiliarioBase):
    id: int
    evento_id: int
    precio_unitario: float

    class Config:
        from_attributes = True


# ─── Registro Financiero ───
class RegistroFinancieroBase(BaseModel):
    evento_id: Optional[int] = None
    presupuesto_id: Optional[int] = None
    tipo: str  # ingreso, egreso
    concepto: str
    monto: float
    notas: Optional[str] = ""


class RegistroFinancieroCreate(RegistroFinancieroBase):
    pass


class RegistroFinancieroOut(RegistroFinancieroBase):
    id: int
    fecha: Optional[datetime] = None

    class Config:
        from_attributes = True


# ─── Presupuesto (calcular simple, sin logística) ───
class PresupuestoItem(BaseModel):
    mobiliario_id: int
    cantidad: int = 1


class PresupuestoRequest(BaseModel):
    cliente_id: int
    items: list[PresupuestoItem]
    costo_traslado: float = 0.0
    costo_mano_obra: float = 0.0


class PresupuestoLinea(BaseModel):
    mobiliario_id: int
    nombre: str
    cantidad: int
    precio_unitario: float
    subtotal: float


class PresupuestoResponse(BaseModel):
    items: list[PresupuestoLinea]
    subtotal_mobiliario: float
    costo_traslado: float
    costo_mano_obra: float
    total: float


# ─── Presupuesto Avanzado (con lugares + logística) ───
class ProductoLugar(BaseModel):
    catalogo_key: str = ""
    mobiliario_id: Optional[int] = None  # alternativa: buscar por ID en vez de nombre
    cantidad: int = 1
    notas: str = ""
    precio_manual: Optional[float] = None


class LugarPresupuesto(BaseModel):
    nombre: str = "General"
    productos: list[ProductoLugar] = []


class PresupuestoAvanzadoRequest(BaseModel):
    cliente_nombre: str = ""
    cliente_id: Optional[int] = None
    fecha_evento: str = ""
    tipo_evento: str = ""
    cantidad_invitados: Optional[int] = None
    localidad: str = "Luján"
    distancia_km: Optional[float] = None
    lugares: list[LugarPresupuesto] = []
    total_override: Optional[float] = None


class LugarCalculado(BaseModel):
    nombre: str
    productos: list[PresupuestoLinea] = []
    subtotal: float = 0.0


class PresupuestoAvanzadoResponse(BaseModel):
    lugares: list[LugarCalculado] = []
    subtotal_mobiliario: float = 0.0
    costo_zona: float = 0.0
    costo_servicio: float = 0.0
    costo_acarreo: float = 0.0
    costo_logistica: float = 0.0
    total: float = 0.0
    total_override: Optional[float] = None
    whatsapp_text: str = ""


# ─── Presupuesto Guardado ───
class PresupuestoSave(BaseModel):
    cliente_nombre: str = ""
    cliente_id: Optional[int] = None
    fecha_evento: str = ""
    tipo_evento: str = ""
    cantidad_invitados: Optional[int] = None
    localidad: str = "Luján"
    distancia_km: Optional[float] = None
    lugares: list[LugarPresupuesto] = []
    subtotal_mobiliario: float = 0.0
    costo_logistica: float = 0.0  # traslado
    costo_armado: float = 0.0  # armado y desarme
    total: float = 0.0
    whatsapp_text: str = ""
    estado: str = "borrador"


class PresupuestoDBOut(BaseModel):
    id: int
    cliente_id: Optional[int] = None
    cliente_nombre: str = ""
    fecha_evento: str = ""
    tipo_evento: str = ""
    cantidad_invitados: Optional[int] = None
    localidad: str = "Luján"
    distancia_km: Optional[float] = None
    lugares: list[LugarPresupuesto] = []
    subtotal_mobiliario: float = 0.0
    costo_logistica: float = 0.0  # traslado
    costo_armado: float = 0.0  # armado y desarme
    total: float = 0.0
    whatsapp_text: str = ""
    estado: str = "borrador"
    evento_id: Optional[int] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ─── Logística ───
class ZonaOut(BaseModel):
    id: int
    nombre: str
    precio: float
    class Config:
        from_attributes = True


class ServicioOut(BaseModel):
    id: int
    nombre: str
    precio: float
    class Config:
        from_attributes = True


class LogisticaConfigOut(BaseModel):
    zonas: list[ZonaOut] = []
    servicios: list[ServicioOut] = []
    acarreo_adicional: float = 0.0
