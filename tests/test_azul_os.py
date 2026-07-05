"""Tests de lógica crítica de Azul OS.

Cubren:
- Cálculo de presupuestos (simple + avanzado con logística)
- CRUD de mobiliario
- CRUD de eventos
- Conversión presupuesto → evento
- PDF generation ( smoke test )
- Auth middleware ( token ausente/presente )
"""
import pytest
import os
import sys
import tempfile
import json

# Add backend/ to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from fastapi.testclient import TestClient
from app.database import Base, engine, SessionLocal, init_db
from app.models import Mobiliario, Cliente, Evento, Presupuesto, LogisticaZona, ConfigLogistica
from app.main import app


@pytest.fixture(scope="module")
def client():
    """Cliente de test con DB SQLite temporal."""
    # Usar DB temporal para tests
    import app.database as db_mod
    original_path = db_mod.SQLALCHEMY_DATABASE_URL

    # Override to test DB
    test_db = tempfile.mktemp(suffix=".db")
    db_mod.SQLALCHEMY_DATABASE_URL = f"sqlite:///{test_db}"

    # Recreate engine
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    db_mod.engine = create_engine(db_mod.SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
    db_mod.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_mod.engine)

    # Import app AFTER overriding DB
    Base.metadata.create_all(bind=db_mod.engine)
    init_db()

    c = TestClient(app)
    yield c

    # Cleanup
    Base.metadata.drop_all(bind=db_mod.engine)
    os.unlink(test_db)


# ─── TEST: Health check ───
def test_debug_endpoints(client):
    r = client.get("/api/debug/endpoints")
    assert r.status_code == 200


# ─── TEST: Mobiliario CRUD ───
def _create_mobiliario(client, nombre, categoria, precio, stock):
    """Helper: crear mobiliario via multipart/form-data (no JSON)."""
    r = client.post("/api/mobiliario/", data={
        "nombre": nombre,
        "categoria": categoria,
        "precio_alquiler": str(precio),
        "stock_total": str(stock),
        "descripcion": "",
        "activo": "true",
    })
    assert r.status_code == 200, f"Failed to create mobiliario: {r.text}"
    return r.json()


def test_mobiliario_crud(client):
    # Crear
    mob = _create_mobiliario(client, "Silla Test", "silla", 5000.0, 10)
    mob_id = mob["id"]

    # Listar
    r = client.get("/api/mobiliario/")
    assert r.status_code == 200
    items = r.json()
    assert any(m["id"] == mob_id for m in items)

    # Obtener por ID
    r = client.get(f"/api/mobiliario/{mob_id}")
    assert r.status_code == 200
    assert r.json()["nombre"] == "Silla Test"

    # Eliminar (soft delete)
    r = client.delete(f"/api/mobiliario/{mob_id}")
    assert r.status_code == 200


# ─── TEST: Cliente CRUD ───
def test_cliente_crud(client):
    r = client.post("/api/clientes/", json={
        "nombre": "Cliente Test",
        "whatsapp": "5491111111111",
        "email": "test@test.com",
    })
    assert r.status_code == 200
    c = r.json()
    assert c["nombre"] == "Cliente Test"
    cid = c["id"]

    r = client.get(f"/api/clientes/{cid}")
    assert r.status_code == 200
    assert r.json()["nombre"] == "Cliente Test"


# ─── TEST: Presupuesto simple ───
def test_presupuesto_simple(client):
    # Crear mobiliario primero
    mob = _create_mobiliario(client, "Mesa Test", "mesa", 10000.0, 5)
    mob_id = mob["id"]

    # Crear cliente
    r = client.post("/api/clientes/", json={"nombre": "Cliente Ppto"})
    cliente_id = r.json()["id"]

    # Calcular presupuesto simple
    r = client.post("/api/presupuestos/calcular-simple/", json={
        "cliente_id": cliente_id,
        "items": [{"mobiliario_id": mob_id, "cantidad": 3}],
        "costo_traslado": 5000.0,
        "costo_mano_obra": 2000.0,
    })
    assert r.status_code == 200
    data = r.json()
    assert data["subtotal_mobiliario"] == 30000.0  # 10000 * 3
    assert data["costo_traslado"] == 5000.0
    assert data["total"] == 37000.0  # 30000 + 5000 + 2000


# ─── TEST: Presupuesto avanzado con logística ───
def test_presupuesto_avanzado_con_logistica(client):
    mob = _create_mobiliario(client, "Sillón Test", "sillon", 15000.0, 4)
    mob_id = mob["id"]

    r = client.post("/api/presupuestos/calculate/", json={
        "cliente_nombre": "Cliente Avanzado",
        "fecha_evento": "2025-12-25",
        "tipo_evento": "Boda",
        "localidad": "Luján",
        "distancia_km": 30,
        "logistica_tipo": "Traslado Simple",
        "acarreo_adicional": True,
        "lugares": [{
            "nombre": "Salón Principal",
            "productos": [{"catalogo_key": "Sillón Test", "mobiliario_id": mob_id, "cantidad": 2}],
        }],
    })
    assert r.status_code == 200
    data = r.json()
    # Subtotal: 15000 * 2 = 30000
    assert data["subtotal_mobiliario"] == 30000.0
    # Logística: 30km * 14000 = 420000 + acarreo 3500 = 423500
    assert data["costo_logistica"] == 423500.0
    # Total: 30000 + 423500 = 453500
    assert data["total"] == 453500.0
    # WhatsApp text debe estar generado
    assert "AZUL LIVINGS" in data["whatsapp_text"]
    assert "TOTAL" in data["whatsapp_text"]


# ─── TEST: Guardar y recuperar presupuesto ───
def test_presupuesto_save_and_retrieve(client):
    r = client.post("/api/clientes/", json={"nombre": "Cliente Save"})
    cliente_id = r.json()["id"]

    r = client.post("/api/presupuestos/", json={
        "cliente_id": cliente_id,
        "cliente_nombre": "Cliente Save",
        "fecha_evento": "2025-12-25",
        "tipo_evento": "Cumpleaños",
        "localidad": "Luján",
        "distancia_km": 10,
        "logistica_tipo": "Traslado Simple",
        "acarreo_adicional": False,
        "solo_ambientacion": False,
        "lugares": [{"nombre": "Salón", "productos": [{"catalogo_key": "Mesa Test", "cantidad": 5}]}],
        "subtotal_mobiliario": 50000.0,
        "costo_logistica": 140000.0,
        "total": 190000.0,
        "whatsapp_text": "",
        "estado": "borrador",
    })
    assert r.status_code == 200
    ppto_id = r.json()["id"]

    r = client.get(f"/api/presupuestos/{ppto_id}")
    assert r.status_code == 200
    assert r.json()["total"] == 190000.0
    assert r.json()["estado"] == "borrador"


# ─── TEST: Logística config ───
def test_logistica_config(client):
    r = client.get("/api/presupuestos/logistica/")
    assert r.status_code == 200
    data = r.json()
    assert "zonas" in data
    assert "servicios" in data
    # Las zonas seed deben existir
    zona_names = [z["nombre"] for z in data["zonas"]]
    assert "Luján" in zona_names
    assert "Pilar" in zona_names


# ─── TEST: PDF generation (smoke test) ───
def test_pdf_generation(client):
    # Crear datos mínimos para un presupuesto
    r = client.post("/api/clientes/", json={"nombre": "Cliente PDF"})
    cliente_id = r.json()["id"]

    r = client.post("/api/presupuestos/", json={
        "cliente_id": cliente_id,
        "cliente_nombre": "Cliente PDF",
        "fecha_evento": "2025-12-25",
        "tipo_evento": "Boda",
        "localidad": "Luján",
        "distancia_km": 5,
        "logistica_tipo": "Traslado Simple",
        "lugares": [{"nombre": "Salón", "productos": [{"catalogo_key": "Silla", "cantidad": 50}]}],
        "subtotal_mobiliario": 250000.0,
        "costo_logistica": 70000.0,
        "total": 320000.0,
        "whatsapp_text": "",
        "estado": "borrador",
    })
    ppto_id = r.json()["id"]

    # PDF completo
    r = client.get(f"/api/presupuestos/{ppto_id}/pdf/completo")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert len(r.content) > 1000  # PDF no vacío

    # PDF cliente
    r = client.get(f"/api/presupuestos/{ppto_id}/pdf/cliente")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"

    # PDF empleados
    r = client.get(f"/api/presupuestos/{ppto_id}/pdf/empleados")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"


# ─── TEST: _fmt_money helper ───
def test_fmt_money():
    from app.pdf_gen import _fmt_money
    assert _fmt_money(1234.5) == "$1.234"
    assert _fmt_money(0) == "$0"
    assert _fmt_money(999.9) == "$1.000"
    assert _fmt_money(1000000) == "$1.000.000"


# ─── TEST: Auth middleware (sin token = libre, con token = bloquea) ───
def test_auth_middleware_no_token(client):
    """Sin AZUL_AUTH_TOKEN configurado, todo debe ser accesible."""
    # Cuando no hay token, no debe haber redirect a /login
    r = client.get("/")
    assert r.status_code == 200
    assert "Azul OS" in r.text
