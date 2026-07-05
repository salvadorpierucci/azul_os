from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os

# Ruta a la DB: relativa al proyecto por defecto, o override via env var
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.environ.get("AZUL_DB_PATH", os.path.join(_PROJECT_ROOT, "data", "azul_os.db"))
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    Base.metadata.create_all(bind=engine)
    # Seed logística si no existe
    from app.models import LogisticaZona, LogisticaServicio, ConfigLogistica, ConfiguracionWhatsApp
    db = SessionLocal()
    try:
        if db.query(LogisticaZona).count() == 0:
            zonas = [
                ("Jáuregui", 0.0),
                ("Pueblo Nuevo", 0.0),
                ("Luján", 5000.0),
                ("General Rodríguez", 8000.0),
                ("Pilar", 12000.0),
                ("Escobar", 15000.0),
                ("Nordelta", 22000.0),
                ("Otro / A convenir", 0.0),
            ]
            for nombre, precio in zonas:
                db.add(LogisticaZona(nombre=nombre, precio=precio))
        if db.query(LogisticaServicio).count() == 0:
            servicios = [
                ("Traslado Simple", 0.0),
                ("Armado y Desarme", 4500.0),
            ]
            for nombre, precio in servicios:
                db.add(LogisticaServicio(nombre=nombre, precio=precio))
        if db.query(ConfigLogistica).count() == 0:
            db.add(ConfigLogistica(clave="acarreo_adicional", valor=3500.0))
            db.add(ConfigLogistica(clave="precio_por_km", valor=14000.0))
        # Seed configuración WhatsApp si no existe
        if db.query(ConfiguracionWhatsApp).count() == 0:
            defaults = [
                ("bot_activo", "true", "Activar/desactivar el bot"),
                ("saludo_texto", "¡Hola! Soy el asistente de Azul Alquileres 🪑", "Texto de bienvenida"),
                ("menu_texto", "Comandos disponibles:\n• *stock* — Ver mobiliario disponible\n• *disponible [fecha]* — Consultar disponibilidad\n• *próximo* — Próximo evento\n• *presupuesto* — Pedir presupuesto\n• *eventos* — Tus eventos\n• *contacto* — Hablar con asesor", "Menú de comandos"),
                ("recordatorio_hs", "48", "Horas antes del evento para recordatorio"),
                ("comando_stock", "true", "Habilitar comando 'stock'"),
                ("comando_disponible", "true", "Habilitar comando 'disponible [fecha]'"),
                ("comando_eventos", "true", "Habilitar comando 'eventos'"),
                ("comando_presupuesto", "true", "Habilitar comando 'presupuesto'"),
            ]
            for clave, valor, descripcion in defaults:
                db.add(ConfiguracionWhatsApp(clave=clave, valor=valor, descripcion=descripcion))
        db.commit()
    finally:
        db.close()
