"""
Fixtures compartidas por todos los módulos de test.

Convención (ver docs/FULLSTACK/README.md): un archivo test_<modulo>.py por
módulo, mapeado 1:1 al spec en FULLSTACK/module_<modulo>.md. Todos comparten
este conftest.py -- no duplicar fixtures de cliente/auth en cada archivo.
"""

import uuid

import pytest
from fastapi.testclient import TestClient

from app.db.database import SessionLocal
from app.main import app
from app.models.models import Cliente, FrecuenciaPago


@pytest.fixture(scope="session")
def client():
    return TestClient(app)


@pytest.fixture(scope="session")
def admin_token(client):
    """Usa el usuario admin ya sembrado en pos.db. Ajusta si tu entorno
    usa otras credenciales (ver docs/aux_pedidos.md Paso 4)."""
    resp = client.post(
        "/api/v1/auth/login",
        data={"username": "admin", "password": "admin123"},
    )
    assert resp.status_code == 200, f"Login falló: {resp.text}"
    return resp.json()["access_token"]


@pytest.fixture(scope="session")
def auth_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def cliente_prueba():
    """Crea un cliente directo en SQLAlchemy, sin pasar por POST /clientes.

    Bypass intencional de INC-02 (frecuencia_pago NOT NULL no expuesto en
    ClienteCreate, ver REPORT.md §4.3 punto 5). Cuando ese bug se corrija,
    este fixture puede cambiarse a un POST real sin tocar los tests que lo
    usan -- por eso vive aquí y no repetido en cada archivo de test.

    no_cliente único por corrida (uuid) para que los tests puedan repetirse
    sin chocar entre sí ni con datos manuales que ya tengas en pos.db.
    """
    db = SessionLocal()
    no_cliente = f"TEST-{uuid.uuid4().hex[:8].upper()}"
    cliente = Cliente(
        no_cliente=no_cliente,
        nombre=f"Cliente Test {no_cliente}",
        colonia="Centro",
        telefono="4440000000",
        frecuencia_pago=FrecuenciaPago.semanal,
        ref_nombre="Ref Test",
        ref_colonia="Centro",
        saldo=0.0,
        estatus="activo",
    )
    db.add(cliente)
    db.commit()
    db.refresh(cliente)
    yield cliente
    db.close()  # no se borra el cliente -- REPORT.md §1: no se conserva data real, se limpia regenerando pos.db
