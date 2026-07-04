"""
Fixtures compartidas por todos los módulos de test.

Convención (ver docs/FULLSTACK/README.md): un archivo test_<modulo>.py por
módulo, mapeado 1:1 al spec en FULLSTACK/module_<modulo>.md. Todos comparten
este conftest.py -- no duplicar fixtures de cliente/auth en cada archivo.
"""

import os
import uuid

import pytest
from fastapi.testclient import TestClient
from passlib.context import CryptContext

from app.db.database import SessionLocal
from app.main import app
from app.models.models import Cliente, FrecuenciaPago, Usuario

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Configurable por si tu entorno usa otro usuario admin -- por defecto no
# depende de que alguien haya reseteado la contraseña a mano (ver
# REPORT.md §4.3: esto costó una sesión completa de ida y vuelta con curl).
TEST_ADMIN_USER = os.environ.get("TEST_ADMIN_USER", "admin")
TEST_ADMIN_PASSWORD = os.environ.get("TEST_ADMIN_PASSWORD", "admin123-test")


@pytest.fixture(scope="session")
def client():
    return TestClient(app)


@pytest.fixture(scope="session", autouse=True)
def _fijar_password_admin():
    """Sobrescribe la contraseña de TEST_ADMIN_USER a un valor conocido antes
    de correr cualquier test -- una sola vez por sesión de pytest. Si el
    usuario no existe, se crea. Elimina la necesidad de resetear la
    contraseña a mano cada vez que se corre la suite en una máquina nueva."""
    db = SessionLocal()
    try:
        usuario = db.query(Usuario).filter(Usuario.usuario == TEST_ADMIN_USER).first()
        hash_ = _pwd_context.hash(TEST_ADMIN_PASSWORD)
        if usuario is None:
            usuario = Usuario(usuario=TEST_ADMIN_USER, password_hash=hash_, rol="admin", activo=1)
            db.add(usuario)
        else:
            usuario.password_hash = hash_
        db.commit()
    finally:
        db.close()


@pytest.fixture(scope="session")
def admin_token(client, _fijar_password_admin):
    resp = client.post(
        "/api/v1/auth/login",
        data={"username": TEST_ADMIN_USER, "password": TEST_ADMIN_PASSWORD},
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
