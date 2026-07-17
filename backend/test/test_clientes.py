"""
Tests del módulo Clientes.

Cubre las tres capas: schema (app/schemas/cliente.py), servicio
(app/services/cliente_service.py) y endpoints (app/api/v1/endpoints/clientes.py).

Fuente de verdad para cada caso: docs/spec/module_clientes.md (autoridad
máxima del módulo) y docs/REGLAS_NEGOCIO.md. Referencias puntuales van en
el docstring de cada test.

SUPUESTOS explícitos (si tu app difiere, ajusta solo estas líneas):
- `get_db` vive en `app.db.database` y `get_current_user` en
  `app.services.auth_service`, ambos overrideables vía
  `app.dependency_overrides` (mismo patrón usado en clientes.py).
- SQLite en memoria alcanza para correr Base.metadata.create_all(); no se
  necesita Alembic para los tests.
- Los tests de endpoint montan `clientes_router` en una FastAPI de prueba
  aislada (no `app.main.app`), para no depender de con qué prefijo
  adicional (p. ej. `/api/v1`) main.py monte el router en producción. El
  router ya trae su propio prefix="/clientes" (ver clientes.py), así que
  las URLs de estos tests son relativas a ese prefijo únicamente.
"""
import calendar
from datetime import date, timedelta

import pytest
from pydantic import ValidationError
from fastapi import FastAPI
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.db.database import Base, get_db
from app.api.v1.endpoints.clientes import router as clientes_router
from app.services.auth_service import get_current_user
from app.models.models import (
    Cliente,
    CarteraVencida,
    Familiar,
    FrecuenciaPago,
    EstatusCliente,
    Apartado,
)
from app.schemas.cliente import ClienteCreate
from app.services import cliente_service as svc


# ──────────────────────────────────────────────────────────────────────────
# FIXTURES
# ──────────────────────────────────────────────────────────────────────────

@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


@pytest.fixture()
def api(db_session):
    """TestClient con get_db y auth overrideados, montando únicamente
    clientes_router en una app aislada -- no usa app.main.app para no
    acoplar estos tests al prefijo con el que main.py registre el router
    en producción. Solo prueba endpoint; la lógica de negocio se prueba
    directo contra el servicio en las demás clases."""
    test_app = FastAPI()
    test_app.include_router(clientes_router)

    def _get_db_override():
        yield db_session

    def _get_current_user_override():
        return object()  # auth_service no es objeto de este módulo

    test_app.dependency_overrides[get_db] = _get_db_override
    test_app.dependency_overrides[get_current_user] = _get_current_user_override
    with TestClient(test_app) as client:
        yield client


def _payload_valido(**overrides) -> dict:
    """Payload mínimo válido para POST /clientes, con overrides puntuales."""
    base = {
        "nombre": "Juan Pérez",
        "colonia": "Centro",
        "telefono": 4151234567,
        "ref_nombre": "María Pérez",
        "ref_colonia": "Centro",
        "ref_telefono": None,
        "frecuencia_pago": "semanal",
    }
    base.update(overrides)
    return base


def _hacer_cliente(db, **overrides) -> Cliente:
    """
    Inserta un Cliente directo por ORM (sin pasar por crear_cliente),
    para poder fijar `saldo` / `fecha_pago_programada` a mano y así probar
    las banderas sin depender de movimientos/abonos (fuera de este módulo).
    """
    defaults = dict(
        no_cliente=overrides.pop("no_cliente", "Centro-001"),
        nombre="Juan Pérez",
        colonia="Centro",
        telefono=4151234567,
        frecuencia_pago=FrecuenciaPago.semanal,
        dia_pago_especifico=None,
        frecuencia_pago_detalle=None,
        ref_nombre="María Pérez",
        ref_colonia="Centro",
        ref_telefono=None,
        saldo=0.0,
        fecha_pago_programada=None,
    )
    defaults.update(overrides)
    cliente = Cliente(**defaults)
    svc.sincronizar_estatus(cliente)
    db.add(cliente)
    db.commit()
    db.refresh(cliente)
    return cliente


def _restar_un_mes(f: date) -> date:
    """Inverso de svc._sumar_un_mes, para construir escenarios de bandera
    naranja con precisión de calendario (no timedelta aproximado)."""
    year = f.year - 1 if f.month == 1 else f.year
    month = 12 if f.month == 1 else f.month - 1
    ultimo_dia_mes = calendar.monthrange(year, month)[1]
    return date(year, month, min(f.day, ultimo_dia_mes))


# ──────────────────────────────────────────────────────────────────────────
# generar_no_cliente()
# ──────────────────────────────────────────────────────────────────────────

class TestGenerarNoCliente:
    def test_primer_cliente_de_una_colonia(self, db_session):
        assert svc.generar_no_cliente(db_session, "Centro") == "Centro-001"

    def test_consecutivo_incrementa(self, db_session):
        _hacer_cliente(db_session, no_cliente="Centro-001")
        assert svc.generar_no_cliente(db_session, "Centro") == "Centro-002"

    def test_consecutivo_independiente_por_colonia(self, db_session):
        _hacer_cliente(db_session, no_cliente="Centro-001")
        assert svc.generar_no_cliente(db_session, "Carrillos") == "Carrillos-001"

    def test_prefijo_normaliza_a_title_case(self, db_session):
        # module_clientes.md: formato {Colonia}-{consecutivo:03d}
        assert svc.generar_no_cliente(db_session, "SAN JUAN") == "San Juan-001"


# ──────────────────────────────────────────────────────────────────────────
# sincronizar_estatus()
# ──────────────────────────────────────────────────────────────────────────

class TestSincronizarEstatus:
    def test_saldo_positivo_es_activo(self):
        cliente = Cliente(saldo=100.0)
        svc.sincronizar_estatus(cliente)
        assert cliente.estatus == "activo"

    def test_saldo_cero_es_inactivo(self):
        cliente = Cliente(saldo=0.0)
        svc.sincronizar_estatus(cliente)
        assert cliente.estatus == "inactivo"


# ──────────────────────────────────────────────────────────────────────────
# ClienteCreate — validaciones del schema
# ──────────────────────────────────────────────────────────────────────────

class TestClienteCreateSchema:
    def test_payload_valido_no_lanza(self):
        ClienteCreate(**_payload_valido())

    @pytest.mark.parametrize("campo", ["nombre", "colonia", "ref_nombre", "ref_colonia"])
    def test_campos_de_texto_vacios_rechazados(self, campo):
        with pytest.raises(ValidationError):
            ClienteCreate(**_payload_valido(**{campo: "   "}))

    def test_strip_de_espacios_en_campos_de_texto(self):
        data = ClienteCreate(**_payload_valido(nombre="  Juan Pérez  "))
        assert data.nombre == "Juan Pérez"

    def test_telefono_no_diez_digitos_rechazado(self):
        with pytest.raises(ValidationError):
            ClienteCreate(**_payload_valido(telefono=12345))

    def test_ref_telefono_none_permitido(self):
        data = ClienteCreate(**_payload_valido(ref_telefono=None))
        assert data.ref_telefono is None

    def test_ref_telefono_no_diez_digitos_rechazado(self):
        with pytest.raises(ValidationError):
            ClienteCreate(**_payload_valido(ref_telefono=123))

    def test_dia_pago_especifico_fuera_de_rango_rechazado(self):
        with pytest.raises(ValidationError):
            ClienteCreate(**_payload_valido(
                frecuencia_pago="dia_especifico_mes", dia_pago_especifico=32,
            ))

    def test_dia_especifico_mes_requiere_dia_pago_especifico(self):
        with pytest.raises(ValidationError):
            ClienteCreate(**_payload_valido(frecuencia_pago="dia_especifico_mes"))

    def test_dia_especifico_mes_con_dia_valido_ok(self):
        data = ClienteCreate(**_payload_valido(
            frecuencia_pago="dia_especifico_mes", dia_pago_especifico=15,
        ))
        assert data.dia_pago_especifico == 15

    def test_otro_requiere_frecuencia_pago_detalle(self):
        with pytest.raises(ValidationError):
            ClienteCreate(**_payload_valido(frecuencia_pago="otro"))

    def test_otro_con_detalle_vacio_rechazado(self):
        with pytest.raises(ValidationError):
            ClienteCreate(**_payload_valido(frecuencia_pago="otro", frecuencia_pago_detalle="   "))

    def test_otro_con_detalle_ok_y_strip(self):
        data = ClienteCreate(**_payload_valido(
            frecuencia_pago="otro", frecuencia_pago_detalle="  paga cuando puede  ",
        ))
        assert data.frecuencia_pago_detalle == "paga cuando puede"

    def test_semanal_no_requiere_campos_condicionales(self):
        data = ClienteCreate(**_payload_valido(frecuencia_pago="semanal"))
        assert data.dia_pago_especifico is None
        assert data.frecuencia_pago_detalle is None

    def test_frecuencia_pago_invalida_rechazada(self):
        with pytest.raises(ValidationError):
            ClienteCreate(**_payload_valido(frecuencia_pago="mensual"))


# ──────────────────────────────────────────────────────────────────────────
# crear_cliente() / obtener_cliente() / buscar_clientes()
# ──────────────────────────────────────────────────────────────────────────

class TestCrearYConsultarClientes:
    def test_crear_cliente_asigna_no_cliente_generado(self, db_session):
        data = ClienteCreate(**_payload_valido(colonia="Centro"))
        cliente = svc.crear_cliente(db_session, data)
        assert cliente.no_cliente == "Centro-001"

    def test_crear_cliente_nace_inactivo_y_sin_saldo(self, db_session):
        data = ClienteCreate(**_payload_valido())
        cliente = svc.crear_cliente(db_session, data)
        assert cliente.saldo == 0.0
        assert cliente.estatus == EstatusCliente.inactivo
        assert cliente.fecha_pago_programada is None

    def test_crear_cliente_persiste_frecuencia_pago(self, db_session):
        # INC-02 (ver cliente_service.py): antes ausente, causaba IntegrityError
        data = ClienteCreate(**_payload_valido(frecuencia_pago="quincenal"))
        cliente = svc.crear_cliente(db_session, data)
        assert cliente.frecuencia_pago == FrecuenciaPago.quincenal

    def test_obtener_cliente_inexistente_devuelve_none(self, db_session):
        assert svc.obtener_cliente(db_session, 9999) is None

    def test_buscar_sin_query_devuelve_todos(self, db_session):
        _hacer_cliente(db_session, no_cliente="Centro-001", nombre="Ana")
        _hacer_cliente(db_session, no_cliente="Centro-002", nombre="Beto")
        assert len(svc.buscar_clientes(db_session, "")) == 2

    def test_buscar_por_nombre_parcial(self, db_session):
        _hacer_cliente(db_session, no_cliente="Centro-001", nombre="Ana López")
        _hacer_cliente(db_session, no_cliente="Centro-002", nombre="Beto Ruiz")
        resultado = svc.buscar_clientes(db_session, "ana")
        assert [c.nombre for c in resultado] == ["Ana López"]

    def test_buscar_por_no_cliente_parcial(self, db_session):
        _hacer_cliente(db_session, no_cliente="Centro-001", nombre="Ana")
        resultado = svc.buscar_clientes(db_session, "centro-001")
        assert len(resultado) == 1


# ──────────────────────────────────────────────────────────────────────────
# Sistema de banderas — module_clientes.md §Sistema de banderas
# ──────────────────────────────────────────────────────────────────────────

class TestBanderaAmarilla:
    """🟡 fecha_pago_programada - hoy <= 2 días (con saldo > 0)."""

    def test_saldo_cero_no_genera_amarilla(self, db_session):
        cliente = _hacer_cliente(
            db_session, saldo=0.0, fecha_pago_programada=date.today() + timedelta(days=1),
        )
        assert svc.calcular_bandera_amarilla(cliente) is False

    def test_fecha_pago_programada_none_no_genera_amarilla(self, db_session):
        cliente = _hacer_cliente(db_session, saldo=100.0, fecha_pago_programada=None)
        assert svc.calcular_bandera_amarilla(cliente) is False

    def test_a_un_dia_de_vencer_es_amarilla(self, db_session):
        cliente = _hacer_cliente(
            db_session, saldo=100.0, fecha_pago_programada=date.today() + timedelta(days=1),
        )
        assert svc.calcular_bandera_amarilla(cliente) is True

    def test_exactamente_en_el_limite_de_2_dias_es_amarilla(self, db_session):
        cliente = _hacer_cliente(
            db_session, saldo=100.0, fecha_pago_programada=date.today() + timedelta(days=2),
        )
        assert svc.calcular_bandera_amarilla(cliente) is True

    def test_a_3_dias_de_vencer_no_es_amarilla(self, db_session):
        cliente = _hacer_cliente(
            db_session, saldo=100.0, fecha_pago_programada=date.today() + timedelta(days=3),
        )
        assert svc.calcular_bandera_amarilla(cliente) is False

    def test_ya_vencido_no_es_amarilla_es_terreno_de_roja(self, db_session):
        cliente = _hacer_cliente(
            db_session, saldo=100.0, fecha_pago_programada=date.today() - timedelta(days=1),
        )
        assert svc.calcular_bandera_amarilla(cliente) is False


class TestBanderaRoja:
    """🔴 hoy > fecha_pago_programada (con saldo > 0)."""

    def test_saldo_cero_no_genera_roja(self, db_session):
        cliente = _hacer_cliente(
            db_session, saldo=0.0, fecha_pago_programada=date.today() - timedelta(days=5),
        )
        assert svc.calcular_bandera_roja(cliente) is False

    def test_fecha_pago_programada_none_no_genera_roja(self, db_session):
        cliente = _hacer_cliente(db_session, saldo=100.0, fecha_pago_programada=None)
        assert svc.calcular_bandera_roja(cliente) is False

    def test_hoy_igual_a_fecha_programada_no_es_roja(self, db_session):
        # condición es estrictamente "hoy > fecha_pago_programada"
        cliente = _hacer_cliente(db_session, saldo=100.0, fecha_pago_programada=date.today())
        assert svc.calcular_bandera_roja(cliente) is False

    def test_vencido_ayer_es_roja(self, db_session):
        cliente = _hacer_cliente(
            db_session, saldo=100.0, fecha_pago_programada=date.today() - timedelta(days=1),
        )
        assert svc.calcular_bandera_roja(cliente) is True

    def test_fecha_futura_no_es_roja(self, db_session):
        cliente = _hacer_cliente(
            db_session, saldo=100.0, fecha_pago_programada=date.today() + timedelta(days=10),
        )
        assert svc.calcular_bandera_roja(cliente) is False


class TestBanderaNaranja:
    """🟠 apartado abierto a <= 5 días de cumplir 1 mes desde fecha_apartado."""

    def test_sin_apartado_no_genera_naranja(self, db_session):
        cliente = _hacer_cliente(db_session)
        assert svc.calcular_bandera_naranja(db_session, cliente) is False

    def test_apartado_recien_abierto_lejos_de_vencer(self, db_session):
        cliente = _hacer_cliente(db_session)
        db_session.add(Apartado(
            id_cliente=cliente.id_cliente, fecha_apartado=date.today(),
            monto_primer_pago=100.0, saldo_pendiente=500.0,
        ))
        db_session.commit()
        assert svc.calcular_bandera_naranja(db_session, cliente) is False

    def test_apartado_a_5_dias_de_vencer_es_naranja(self, db_session):
        cliente = _hacer_cliente(db_session)
        fecha_apartado = _restar_un_mes(date.today() + timedelta(days=5))
        db_session.add(Apartado(
            id_cliente=cliente.id_cliente, fecha_apartado=fecha_apartado,
            monto_primer_pago=100.0, saldo_pendiente=500.0,
        ))
        db_session.commit()
        assert svc.calcular_bandera_naranja(db_session, cliente) is True

    def test_apartado_liquidado_no_genera_naranja(self, db_session):
        cliente = _hacer_cliente(db_session)
        fecha_apartado = _restar_un_mes(date.today() + timedelta(days=5))
        db_session.add(Apartado(
            id_cliente=cliente.id_cliente, fecha_apartado=fecha_apartado,
            monto_primer_pago=100.0, saldo_pendiente=0.0, estatus="liquidado",
        ))
        db_session.commit()
        assert svc.calcular_bandera_naranja(db_session, cliente) is False


class TestBanderaNegra:
    """⚫ el cliente tiene bandera_roja Y al menos un familiar también."""

    def test_sin_bandera_roja_propia_es_false_aunque_familiar_sea_roja(self, db_session):
        cliente = _hacer_cliente(
            db_session, no_cliente="Centro-001", saldo=0.0,
        )
        familiar = _hacer_cliente(
            db_session, no_cliente="Centro-002",
            saldo=100.0, fecha_pago_programada=date.today() - timedelta(days=3),
        )
        svc.vincular_familiar(db_session, cliente.id_cliente, familiar.id_cliente)
        assert svc.calcular_bandera_negra(db_session, cliente) is False

    def test_bandera_roja_propia_sin_familiares_es_false(self, db_session):
        cliente = _hacer_cliente(
            db_session, saldo=100.0, fecha_pago_programada=date.today() - timedelta(days=3),
        )
        assert svc.calcular_bandera_negra(db_session, cliente) is False

    def test_bandera_roja_propia_y_familiar_sin_roja_es_false(self, db_session):
        cliente = _hacer_cliente(
            db_session, no_cliente="Centro-001",
            saldo=100.0, fecha_pago_programada=date.today() - timedelta(days=3),
        )
        familiar = _hacer_cliente(db_session, no_cliente="Centro-002", saldo=0.0)
        svc.vincular_familiar(db_session, cliente.id_cliente, familiar.id_cliente)
        assert svc.calcular_bandera_negra(db_session, cliente) is False

    def test_bandera_roja_propia_y_familiar_con_roja_es_true(self, db_session):
        cliente = _hacer_cliente(
            db_session, no_cliente="Centro-001",
            saldo=100.0, fecha_pago_programada=date.today() - timedelta(days=3),
        )
        familiar = _hacer_cliente(
            db_session, no_cliente="Centro-002",
            saldo=200.0, fecha_pago_programada=date.today() - timedelta(days=1),
        )
        svc.vincular_familiar(db_session, cliente.id_cliente, familiar.id_cliente)
        assert svc.calcular_bandera_negra(db_session, cliente) is True

    def test_funciona_sin_importar_el_orden_de_declaracion_del_par(self, db_session):
        # cliente termina como id_cliente_b del vínculo (id mayor); confirma
        # que listar_familiares() normaliza la perspectiva correctamente.
        familiar = _hacer_cliente(
            db_session, no_cliente="Centro-001",
            saldo=200.0, fecha_pago_programada=date.today() - timedelta(days=1),
        )
        cliente = _hacer_cliente(
            db_session, no_cliente="Centro-002",
            saldo=100.0, fecha_pago_programada=date.today() - timedelta(days=3),
        )
        svc.vincular_familiar(db_session, familiar.id_cliente, cliente.id_cliente)
        assert svc.calcular_bandera_negra(db_session, cliente) is True


# ──────────────────────────────────────────────────────────────────────────
# Familiares — vincular / desvincular / listar
# ──────────────────────────────────────────────────────────────────────────

class TestFamiliares:
    def test_vincular_normaliza_orden_id_a_menor_que_id_b(self, db_session):
        c1 = _hacer_cliente(db_session, no_cliente="Centro-001")
        c2 = _hacer_cliente(db_session, no_cliente="Centro-002")
        # pasa el mayor primero a propósito
        vinculo = svc.vincular_familiar(db_session, c2.id_cliente, c1.id_cliente)
        assert vinculo.id_cliente_a == min(c1.id_cliente, c2.id_cliente)
        assert vinculo.id_cliente_b == max(c1.id_cliente, c2.id_cliente)

    def test_vincular_rechaza_autovinculo(self, db_session):
        c1 = _hacer_cliente(db_session, no_cliente="Centro-001")
        with pytest.raises(ValueError):
            svc.vincular_familiar(db_session, c1.id_cliente, c1.id_cliente)

    def test_vincular_rechaza_cliente_inexistente(self, db_session):
        c1 = _hacer_cliente(db_session, no_cliente="Centro-001")
        with pytest.raises(ValueError):
            svc.vincular_familiar(db_session, c1.id_cliente, 9999)

    def test_vincular_rechaza_par_ya_vinculado_en_cualquier_orden(self, db_session):
        c1 = _hacer_cliente(db_session, no_cliente="Centro-001")
        c2 = _hacer_cliente(db_session, no_cliente="Centro-002")
        svc.vincular_familiar(db_session, c1.id_cliente, c2.id_cliente)
        with pytest.raises(ValueError):
            svc.vincular_familiar(db_session, c2.id_cliente, c1.id_cliente)

    def test_vincular_respeta_tope_de_4_para_cliente_a(self, db_session):
        eje = _hacer_cliente(db_session, no_cliente="Centro-001")
        for i in range(4):
            otro = _hacer_cliente(db_session, no_cliente=f"Centro-{i+2:03d}")
            svc.vincular_familiar(db_session, eje.id_cliente, otro.id_cliente)
        quinto = _hacer_cliente(db_session, no_cliente="Centro-999")
        with pytest.raises(ValueError):
            svc.vincular_familiar(db_session, eje.id_cliente, quinto.id_cliente)

    def test_vincular_respeta_tope_de_4_para_cliente_b(self, db_session):
        # mismo tope, pero el que ya tiene 4 es el segundo argumento
        eje = _hacer_cliente(db_session, no_cliente="Centro-001")
        for i in range(4):
            otro = _hacer_cliente(db_session, no_cliente=f"Centro-{i+2:03d}")
            svc.vincular_familiar(db_session, otro.id_cliente, eje.id_cliente)
        quinto = _hacer_cliente(db_session, no_cliente="Centro-999")
        with pytest.raises(ValueError):
            svc.vincular_familiar(db_session, quinto.id_cliente, eje.id_cliente)

    def test_listar_familiares_perspectiva_de_ambos_lados_del_par(self, db_session):
        c1 = _hacer_cliente(db_session, no_cliente="Centro-001", nombre="Ana")
        c2 = _hacer_cliente(db_session, no_cliente="Centro-002", nombre="Beto")
        svc.vincular_familiar(db_session, c1.id_cliente, c2.id_cliente)

        desde_c1 = svc.listar_familiares(db_session, c1.id_cliente)
        desde_c2 = svc.listar_familiares(db_session, c2.id_cliente)

        assert len(desde_c1) == 1 and desde_c1[0]["id_cliente_relacionado"] == c2.id_cliente
        assert len(desde_c2) == 1 and desde_c2[0]["id_cliente_relacionado"] == c1.id_cliente

    def test_desvincular_elimina_el_registro(self, db_session):
        c1 = _hacer_cliente(db_session, no_cliente="Centro-001")
        c2 = _hacer_cliente(db_session, no_cliente="Centro-002")
        vinculo = svc.vincular_familiar(db_session, c1.id_cliente, c2.id_cliente)

        svc.desvincular_familiar(db_session, c1.id_cliente, vinculo.id_vinculo)

        assert svc.listar_familiares(db_session, c1.id_cliente) == []
        assert svc.listar_familiares(db_session, c2.id_cliente) == []

    def test_desvincular_rechaza_vinculo_inexistente(self, db_session):
        c1 = _hacer_cliente(db_session, no_cliente="Centro-001")
        with pytest.raises(ValueError):
            svc.desvincular_familiar(db_session, c1.id_cliente, 9999)

    def test_desvincular_rechaza_cliente_ajeno_al_vinculo(self, db_session):
        c1 = _hacer_cliente(db_session, no_cliente="Centro-001")
        c2 = _hacer_cliente(db_session, no_cliente="Centro-002")
        c3 = _hacer_cliente(db_session, no_cliente="Centro-003")
        vinculo = svc.vincular_familiar(db_session, c1.id_cliente, c2.id_cliente)
        with pytest.raises(ValueError):
            svc.desvincular_familiar(db_session, c3.id_cliente, vinculo.id_vinculo)


# ──────────────────────────────────────────────────────────────────────────
# cancelar_cliente() — module_clientes.md §Operación "Cancelar Cliente"
# ──────────────────────────────────────────────────────────────────────────

class TestCancelarCliente:
    def _cliente_moroso(self, db_session, **overrides):
        defaults = dict(
            no_cliente="Centro-001", nombre="Juan Pérez", saldo=500.0,
            fecha_pago_programada=date.today() - timedelta(days=10),
        )
        defaults.update(overrides)
        return _hacer_cliente(db_session, **defaults)

    def test_rechaza_cliente_inexistente(self, db_session):
        with pytest.raises(ValueError):
            svc.cancelar_cliente(db_session, 9999)

    def test_rechaza_sin_bandera_roja(self, db_session):
        cliente = _hacer_cliente(db_session, saldo=0.0)  # sin morosidad
        with pytest.raises(ValueError):
            svc.cancelar_cliente(db_session, cliente.id_cliente)

    def test_snapshot_correcto_en_cartera_vencida(self, db_session):
        cliente = self._cliente_moroso(db_session)
        snapshot = svc.cancelar_cliente(db_session, cliente.id_cliente)

        assert snapshot.no_cliente_original == "Centro-001"
        assert snapshot.nombre == "Juan Pérez"
        assert snapshot.saldo_cancelado == 500.0
        assert snapshot.fecha_cancelacion == date.today().isoformat()
        # queda persistido en la tabla
        assert db_session.query(CarteraVencida).count() == 1

    def test_limpia_slot_pero_conserva_no_cliente_e_id(self, db_session):
        # module_clientes.md: el no_cliente y el id_cliente NO cambian
        cliente = self._cliente_moroso(db_session)
        id_original = cliente.id_cliente
        no_cliente_original = cliente.no_cliente

        svc.cancelar_cliente(db_session, cliente.id_cliente)
        db_session.refresh(cliente)

        assert cliente.id_cliente == id_original
        assert cliente.no_cliente == no_cliente_original
        assert cliente.nombre == ""
        assert cliente.telefono == 0
        assert cliente.frecuencia_pago == FrecuenciaPago.otro
        assert cliente.dia_pago_especifico is None
        assert cliente.frecuencia_pago_detalle == "slot disponible"
        assert cliente.ref_nombre == ""
        assert cliente.ref_colonia == ""
        assert cliente.ref_telefono is None
        assert cliente.fecha_pago_programada is None

    def test_saldo_queda_en_cero_y_estatus_inactivo(self, db_session):
        cliente = self._cliente_moroso(db_session)
        svc.cancelar_cliente(db_session, cliente.id_cliente)
        db_session.refresh(cliente)
        assert cliente.saldo == 0.0
        assert cliente.estatus == EstatusCliente.inactivo

    def test_id_cliente_del_familiar_no_se_ve_afectado(self, db_session):
        # cancelar un cliente no debe tocar sus vínculos familiares
        cliente = self._cliente_moroso(db_session, no_cliente="Centro-001")
        familiar = _hacer_cliente(db_session, no_cliente="Centro-002")
        svc.vincular_familiar(db_session, cliente.id_cliente, familiar.id_cliente)

        svc.cancelar_cliente(db_session, cliente.id_cliente)

        assert len(svc.listar_familiares(db_session, familiar.id_cliente)) == 1


# ──────────────────────────────────────────────────────────────────────────
# Endpoints — app/api/v1/endpoints/clientes.py
# ──────────────────────────────────────────────────────────────────────────

class TestEndpointsClientes:
    def test_post_clientes_crea_y_devuelve_las_4_banderas(self, api):
        resp = api.post("/clientes", json=_payload_valido())
        assert resp.status_code == 201
        body = resp.json()
        assert body["no_cliente"] == "Centro-001"
        for campo in ("bandera_amarilla", "bandera_roja", "bandera_naranja", "bandera_negra"):
            assert campo in body and body[campo] is False

    def test_post_clientes_rechaza_payload_invalido(self, api):
        resp = api.post("/clientes", json=_payload_valido(telefono=123))
        assert resp.status_code == 422

    def test_get_clientes_lista_resumen(self, api):
        api.post("/clientes", json=_payload_valido())
        resp = api.get("/clientes")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_get_cliente_detalle_404_si_no_existe(self, api):
        resp = api.get("/clientes/9999")
        assert resp.status_code == 404

    def test_get_cliente_detalle_ok(self, api):
        creado = api.post("/clientes", json=_payload_valido()).json()
        resp = api.get(f"/clientes/{creado['id_cliente']}")
        assert resp.status_code == 200
        assert resp.json()["no_cliente"] == creado["no_cliente"]

    def test_cancelar_404_si_cliente_no_existe(self, api):
        resp = api.post("/clientes/9999/cancelar")
        assert resp.status_code == 404

    def test_cancelar_400_si_no_esta_en_bandera_roja(self, api):
        creado = api.post("/clientes", json=_payload_valido()).json()
        resp = api.post(f"/clientes/{creado['id_cliente']}/cancelar")
        assert resp.status_code == 400

    def test_familiares_flujo_completo(self, api, db_session):
        c1 = api.post("/clientes", json=_payload_valido(colonia="Centro")).json()
        c2 = api.post("/clientes", json=_payload_valido(colonia="Carrillos")).json()

        vinc = api.post(
            f"/clientes/{c1['id_cliente']}/familiares",
            json={"id_cliente_relacionado": c2["id_cliente"]},
        )
        assert vinc.status_code == 201
        assert vinc.json()["id_cliente_relacionado"] == c2["id_cliente"]

        listado = api.get(f"/clientes/{c1['id_cliente']}/familiares")
        assert listado.status_code == 200
        assert len(listado.json()) == 1

        borrado = api.delete(
            f"/clientes/{c1['id_cliente']}/familiares/{vinc.json()['id_vinculo']}"
        )
        assert borrado.status_code == 204
        assert api.get(f"/clientes/{c1['id_cliente']}/familiares").json() == []

    def test_vincular_familiar_400_si_ya_vinculados(self, api):
        c1 = api.post("/clientes", json=_payload_valido(colonia="Centro")).json()
        c2 = api.post("/clientes", json=_payload_valido(colonia="Carrillos")).json()
        api.post(f"/clientes/{c1['id_cliente']}/familiares",
                 json={"id_cliente_relacionado": c2["id_cliente"]})
        resp = api.post(f"/clientes/{c1['id_cliente']}/familiares",
                         json={"id_cliente_relacionado": c2["id_cliente"]})
        assert resp.status_code == 400

    def test_desvincular_404_si_vinculo_no_existe(self, api):
        c1 = api.post("/clientes", json=_payload_valido()).json()
        resp = api.delete(f"/clientes/{c1['id_cliente']}/familiares/9999")
        assert resp.status_code == 404
