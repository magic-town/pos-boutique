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
from app.models.models import Cliente, Usuario

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
def cliente_prueba(client, auth_headers):
    """Crea un cliente vía POST /api/v1/clientes (endpoint real).

    Ya NO es el bypass SQLAlchemy anterior. Ese bypass existía únicamente
    por INC-02 (frecuencia_pago NOT NULL no expuesto en ClienteCreate, ver
    REPORT.md §4.3 punto 11) -- INC-02 está resuelto en schemas/cliente.py
    y services/cliente_service.py, así que el workaround ya no aplica (ver
    test/README.md, sección "Por qué cliente_prueba usa POST
    /api/v1/clientes").

    no_cliente único por corrida (uuid en la colonia) para que los tests
    puedan repetirse sin chocar entre sí ni con datos manuales que ya
    tengas en pos.db, y para no interferir con el consecutivo por colonia
    que prueba test_clientes.py (test_no_cliente_consecutivo_por_colonia).
    """
    sufijo = uuid.uuid4().hex[:8].upper()
    payload = {
        "nombre": f"Cliente Test {sufijo}",
        "colonia": f"FixtureTest{sufijo}",
        "telefono": 4440000000,
        "ref_nombre": "Ref Test",
        "ref_colonia": "Centro",
        "ref_telefono": None,
        "frecuencia_pago": "semanal",
        "dia_pago_especifico": None,
        "frecuencia_pago_detalle": None,
    }
    resp = client.post("/api/v1/clientes", json=payload, headers=auth_headers)
    assert resp.status_code == 201, (
        f"cliente_prueba: POST /api/v1/clientes falló "
        f"({resp.status_code}): {resp.text}"
    )
    creado = resp.json()

    db = SessionLocal()
    cliente = db.query(Cliente).get(creado["id_cliente"])
    yield cliente
    db.close()  # no se borra el cliente -- REPORT.md §1: no se conserva data real, se limpia regenerando pos.db


@pytest.fixture
def db_session():
    """Sesión de BD directa, para los tests que necesitan leer o preparar
    estado que no se arma cómodamente vía la API pública (ej. dejar un
    cliente con un `saldo`/`estatus` de partida específico para probar la
    sincronización automática -- ver test_clientes.py / test_movimientos.py).
    Ya no aplica el caso original de TestRehabilitarCliente (retirado);
    se conserva porque sigue siendo útil para otros módulos.

    Function-scoped a propósito: cada test recibe su propia sesión y la
    cierra al terminar, sin compartir estado con otros tests ni con
    `client`/`admin_token` (esos sí son session-scoped porque login y
    TestClient son costosos de recrear; esto no lo es).
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
