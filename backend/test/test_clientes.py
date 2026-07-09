"""
test_clientes.py — mapeado 1:1 a test/casos_clientes.md y a
FULLSTACK/module_clientes.md.

✅ RUTAS CONFIRMADAS contra `app/api/v1/endpoints/clientes.py` real:
`POST /api/v1/clientes`, `GET /api/v1/clientes/{id_cliente}`,
`GET /api/v1/clientes?q=`. Las 3 protegidas con `Depends(get_current_user)`
— requieren `auth_headers`.

⚠️ Un detalle sin confirmar todavía: `GET /clientes` responde con
`response_model=list[ClienteResumen]`, no `ClienteRead` — ya se confirmó
en corrida real que expone `nombre` y `no_cliente` (los campos que leen
`test_busqueda_por_nombre_parcial` / `test_busqueda_por_no_cliente_parcial`
de abajo), así que este punto queda cerrado.

**"Rehabilitar Cliente" se quitó** (endpoint, servicio y los 3 tests que lo
cubrían): revisión de negocio confirmó que `estatus` no es un campo que la
operadora edite nunca, ni siquiera desde "Editar Cliente" -- es derivado
de `saldo` y se sincroniza en automático (`cliente_service.sincronizar_estatus`)
en cada punto de Pedidos o Movimientos que toque el saldo. Ver la nota al
final de la sección 2 de este archivo. El ciclo `inactivo -> activo ->
inactivo` se prueba en `test_pedidos.py` (via surtir/devolución/cancelación),
no aquí -- este archivo solo cubre el alta y la consulta.

- Fixtures usadas de conftest.py: `client` (TestClient) y `auth_headers`
  (headers con JWT real) — session-scoped, compartidas con el resto de la
  suite. `db_session` (function-scoped) ya no se usa en este archivo tras
  quitar "Rehabilitar Cliente" — se deja en conftest.py por si otro módulo
  la necesita (ej. Movimientos).
- "Editar Cliente" no se prueba: no existe `editar_cliente` en
  cliente_service.py todavía.
"""
import uuid
from datetime import date, datetime, timedelta

import pytest

from app.models.models import Apartado, Cliente, EstatusApartado, FormaPago
from app.schemas.apartado import ApartadoArticuloCreate, ApartadoCreate
from app.services.cliente_service import _sumar_un_mes, calcular_bandera_naranja
from app.services.movimiento_service import crear_apartado


def _payload_base(**overrides):
    """Payload válido mínimo (frecuencia_pago = semanal, sin condicionales)."""
    base = {
        "nombre": "Cliente Prueba",
        "colonia": "Centro",
        "telefono": 5512345678,
        "ref_nombre": "Referencia Prueba",
        "ref_colonia": "Centro",
        "ref_telefono": None,
        "frecuencia_pago": "semanal",
        "dia_pago_especifico": None,
        "frecuencia_pago_detalle": None,
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# 1. Registrar Cliente
# ---------------------------------------------------------------------------

class TestRegistrarCliente:

    @pytest.mark.parametrize("frecuencia", ["semanal", "quincenal"])
    def test_alta_valida_sin_condicionales(self, client, auth_headers, frecuencia):
        # Casos 1.1 / 1.2
        payload = _payload_base(frecuencia_pago=frecuencia)
        resp = client.post("/api/v1/clientes", json=payload, headers=auth_headers)
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["no_cliente"]
        assert data["saldo"] == 0
        assert data["estatus"] == "inactivo"  # nace inactivo -- se activa al recibir el primer producto (ver test_pedidos.py)
        assert data["fecha_pago_programada"] is None

    def test_alta_valida_dia_especifico_mes(self, client, auth_headers):
        # Caso 1.3
        payload = _payload_base(frecuencia_pago="dia_especifico_mes", dia_pago_especifico=15)
        resp = client.post("/api/v1/clientes", json=payload, headers=auth_headers)
        assert resp.status_code == 201, resp.text
        assert resp.json()["dia_pago_especifico"] == 15

    def test_dia_especifico_mes_sin_dia(self, client, auth_headers):
        # Caso 1.4 — INC-02
        payload = _payload_base(frecuencia_pago="dia_especifico_mes", dia_pago_especifico=None)
        resp = client.post("/api/v1/clientes", json=payload, headers=auth_headers)
        assert resp.status_code == 422

    def test_estatus_no_es_capturable_al_registrar(self, client, auth_headers):
        # `estatus` es derivado -- aunque se envíe en el payload, se ignora
        # o el schema lo rechaza; nunca debe quedar en "activo" al registrar.
        payload = _payload_base()
        payload["estatus"] = "activo"
        resp = client.post("/api/v1/clientes", json=payload, headers=auth_headers)
        if resp.status_code == 201:
            assert resp.json()["estatus"] == "inactivo"
        else:
            assert resp.status_code == 422

    @pytest.mark.parametrize("dia", [0, 32])
    def test_dia_especifico_fuera_de_rango(self, client, auth_headers, dia):
        # Caso 1.5
        payload = _payload_base(frecuencia_pago="dia_especifico_mes", dia_pago_especifico=dia)
        resp = client.post("/api/v1/clientes", json=payload, headers=auth_headers)
        assert resp.status_code == 422

    def test_alta_valida_otro_con_detalle(self, client, auth_headers):
        # Caso 1.6
        payload = _payload_base(frecuencia_pago="otro", frecuencia_pago_detalle="Paga cada 10 días, acuerdo verbal")
        resp = client.post("/api/v1/clientes", json=payload, headers=auth_headers)
        assert resp.status_code == 201, resp.text
        assert resp.json()["frecuencia_pago_detalle"] == "Paga cada 10 días, acuerdo verbal"

    @pytest.mark.parametrize("detalle", [None, "", "   "])
    def test_otro_sin_detalle(self, client, auth_headers, detalle):
        # Caso 1.7
        payload = _payload_base(frecuencia_pago="otro", frecuencia_pago_detalle=detalle)
        resp = client.post("/api/v1/clientes", json=payload, headers=auth_headers)
        assert resp.status_code == 422

    @pytest.mark.parametrize("telefono", [551234567, 55123456789])  # 9 y 11 dígitos
    def test_telefono_digitos_invalidos(self, client, auth_headers, telefono):
        # Caso 1.8 — regresión INC-01
        payload = _payload_base(telefono=telefono)
        resp = client.post("/api/v1/clientes", json=payload, headers=auth_headers)
        assert resp.status_code == 422

    @pytest.mark.parametrize("campo", ["nombre", "colonia", "ref_nombre", "ref_colonia"])
    def test_campos_obligatorios_vacios(self, client, auth_headers, campo):
        # Caso 1.9
        payload = _payload_base(**{campo: "   "})
        resp = client.post("/api/v1/clientes", json=payload, headers=auth_headers)
        assert resp.status_code == 422

    @pytest.mark.parametrize("campo,limite", [
        ("nombre", 40), ("colonia", 20), ("ref_nombre", 40),
        ("ref_colonia", 40), ("frecuencia_pago_detalle", 60),
    ])
    def test_longitud_maxima_excedida(self, client, auth_headers, campo, limite):
        # Caso 1.10 — INC-18
        overrides = {campo: "a" * (limite + 1)}
        if campo == "frecuencia_pago_detalle":
            overrides["frecuencia_pago"] = "otro"
        payload = _payload_base(**overrides)
        resp = client.post("/api/v1/clientes", json=payload, headers=auth_headers)
        assert resp.status_code == 422, f"{campo} debería rechazar {limite + 1} caracteres"

    def test_ref_telefono_ausente_es_valido(self, client, auth_headers):
        # Caso 1.11
        payload = _payload_base(ref_telefono=None)
        resp = client.post("/api/v1/clientes", json=payload, headers=auth_headers)
        assert resp.status_code == 201, resp.text

    def test_no_cliente_consecutivo_por_colonia(self, client, auth_headers):
        # Caso 1.12 — colonia única por corrida para no chocar con otros tests
        colonia = f"Colonia{uuid.uuid4().hex[:6]}"
        payload = _payload_base(colonia=colonia)
        r1 = client.post("/api/v1/clientes", json=payload, headers=auth_headers)
        r2 = client.post("/api/v1/clientes", json=payload, headers=auth_headers)
        assert r1.status_code == 201 and r2.status_code == 201
        no_1, no_2 = r1.json()["no_cliente"], r2.json()["no_cliente"]
        assert no_1.endswith("-001")
        assert no_2.endswith("-002")

    def test_no_cliente_normaliza_mayusculas(self, client, auth_headers):
        # Caso 1.13
        colonia = f"colonia{uuid.uuid4().hex[:6]}"
        payload = _payload_base(colonia=colonia)
        resp = client.post("/api/v1/clientes", json=payload, headers=auth_headers)
        assert resp.status_code == 201, resp.text
        assert resp.json()["no_cliente"].startswith(colonia.title())


# ---------------------------------------------------------------------------
# 2. Consulta Cliente
# ---------------------------------------------------------------------------

class TestConsultaCliente:

    def test_get_por_id_existente(self, client, auth_headers):
        # Caso 2.1
        payload = _payload_base(frecuencia_pago="dia_especifico_mes", dia_pago_especifico=10)
        creado = client.post("/api/v1/clientes", json=payload, headers=auth_headers).json()
        resp = client.get(f"/api/v1/clientes/{creado['id_cliente']}", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["dia_pago_especifico"] == 10
        assert data["fecha_pago_programada"] is None
        assert "fecha_registro" in data

    def test_get_por_id_inexistente(self, client, auth_headers):
        # Caso 2.2 — comportamiento del 404 no confirmado contra el endpoint real
        resp = client.get("/api/v1/clientes/999999", headers=auth_headers)
        assert resp.status_code == 404

    def test_busqueda_por_nombre_parcial(self, client, auth_headers):
        # Caso 2.3
        nombre_unico = f"Buscable{uuid.uuid4().hex[:6]}"
        client.post("/api/v1/clientes", json=_payload_base(nombre=nombre_unico), headers=auth_headers)
        resp = client.get(f"/api/v1/clientes?q={nombre_unico}", headers=auth_headers)
        assert resp.status_code == 200
        resultados = resp.json()
        assert any(c["nombre"] == nombre_unico for c in resultados)

    def test_busqueda_por_no_cliente_parcial(self, client, auth_headers):
        # Caso 2.4
        colonia = f"Buscacol{uuid.uuid4().hex[:6]}"
        creado = client.post("/api/v1/clientes", json=_payload_base(colonia=colonia), headers=auth_headers).json()
        resp = client.get(f"/api/v1/clientes?q={creado['no_cliente']}", headers=auth_headers)
        assert resp.status_code == 200
        assert any(c["no_cliente"] == creado["no_cliente"] for c in resp.json())

    def test_busqueda_vacia_devuelve_todos(self, client, auth_headers):
        # Caso 2.5
        resp = client.get("/api/v1/clientes?q=", headers=auth_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


# ---------------------------------------------------------------------------
# 3. Bandera Naranja
# (module_movimientos.md §"Bandera naranja"; REPORT.md §5 Nivel 3, punto 7.
# calcular_bandera_naranja() vive en cliente_service.py, fuera de
# sincronizar_estatus() -- no toca `clientes.estatus`, se calcula al vuelo
# y se asigna al objeto Cliente antes de serializar ClienteRead.)
# ---------------------------------------------------------------------------

def _crear_apartado_para_cliente(db_session, id_cliente, precio=300.0, monto_primer_pago=100.0):
    """Apartado de 1 artículo manual (sin id_producto) -- no depende de
    Inventario, mismo criterio que test_movimientos.py."""
    data = ApartadoCreate(
        id_cliente=id_cliente,
        articulos=[ApartadoArticuloCreate(id_producto=None, precio_producto=precio)],
        monto_primer_pago=monto_primer_pago,
        forma_pago=FormaPago.efectivo,
    )
    return crear_apartado(db_session, data)


def _fijar_fecha_apartado(db_session, id_apartado, fecha):
    apartado = db_session.query(Apartado).get(id_apartado)
    apartado.fecha_apartado = datetime.combine(fecha, datetime.min.time())
    db_session.commit()
    return apartado


def _fecha_apartado_para_vencimiento(vencimiento):
    """Encuentra la fecha_apartado tal que _sumar_un_mes(fecha_apartado) ==
    vencimiento -- por búsqueda directa contra la función real (no duplica
    la lógica de calendario/clamp de fin de mes)."""
    for dias in range(27, 32):
        candidata = vencimiento - timedelta(days=dias)
        if _sumar_un_mes(candidata) == vencimiento:
            return candidata
    raise AssertionError(f"No se encontró fecha_apartado para vencimiento {vencimiento}")


class TestSumarUnMes:
    """Unitario, sin DB -- el clamp de fin de mes es el detalle más frágil
    de calcular_bandera_naranja() y merece su propio caso, independiente
    de la fecha real del día en que se corra la suite."""

    def test_dia_normal(self):
        assert _sumar_un_mes(date(2024, 3, 10)) == date(2024, 4, 10)

    def test_31_enero_a_febrero_bisiesto(self):
        assert _sumar_un_mes(date(2024, 1, 31)) == date(2024, 2, 29)

    def test_31_enero_a_febrero_no_bisiesto(self):
        assert _sumar_un_mes(date(2023, 1, 31)) == date(2023, 2, 28)

    def test_diciembre_cruza_anio(self):
        assert _sumar_un_mes(date(2023, 12, 15)) == date(2024, 1, 15)


class TestCalcularBanderaNaranja:
    """Directo contra el service (calcular_bandera_naranja(db, cliente)),
    sin pasar por el endpoint -- aísla la lógica de umbral de la mecánica
    de asignación al schema (esa se prueba en TestBanderaNaranjaEndpoint)."""

    def test_false_sin_apartado_abierto(self, client, auth_headers, db_session):
        creado = client.post("/api/v1/clientes", json=_payload_base(), headers=auth_headers).json()
        cliente = db_session.query(Cliente).get(creado["id_cliente"])
        assert calcular_bandera_naranja(db_session, cliente) is False

    def test_false_recien_creado_lejos_del_vencimiento(self, client, auth_headers, db_session):
        creado = client.post("/api/v1/clientes", json=_payload_base(), headers=auth_headers).json()
        _crear_apartado_para_cliente(db_session, creado["id_cliente"])
        cliente = db_session.query(Cliente).get(creado["id_cliente"])
        assert calcular_bandera_naranja(db_session, cliente) is False

    def test_false_un_dia_antes_del_umbral(self, client, auth_headers, db_session):
        creado = client.post("/api/v1/clientes", json=_payload_base(), headers=auth_headers).json()
        apartado = _crear_apartado_para_cliente(db_session, creado["id_cliente"])

        vencimiento = date.today() + timedelta(days=6)  # umbral quedaría mañana, no hoy
        fecha_apartado = _fecha_apartado_para_vencimiento(vencimiento)
        _fijar_fecha_apartado(db_session, apartado.id_apartado, fecha_apartado)

        cliente = db_session.query(Cliente).get(creado["id_cliente"])
        assert calcular_bandera_naranja(db_session, cliente) is False

    def test_true_justo_en_el_umbral(self, client, auth_headers, db_session):
        creado = client.post("/api/v1/clientes", json=_payload_base(), headers=auth_headers).json()
        apartado = _crear_apartado_para_cliente(db_session, creado["id_cliente"])

        vencimiento = date.today() + timedelta(days=5)  # umbral (vencimiento - 5) == hoy
        fecha_apartado = _fecha_apartado_para_vencimiento(vencimiento)
        _fijar_fecha_apartado(db_session, apartado.id_apartado, fecha_apartado)

        cliente = db_session.query(Cliente).get(creado["id_cliente"])
        assert calcular_bandera_naranja(db_session, cliente) is True

    def test_true_apartado_ya_vencido(self, client, auth_headers, db_session):
        creado = client.post("/api/v1/clientes", json=_payload_base(), headers=auth_headers).json()
        apartado = _crear_apartado_para_cliente(db_session, creado["id_cliente"])
        _fijar_fecha_apartado(db_session, apartado.id_apartado, date.today() - timedelta(days=60))

        cliente = db_session.query(Cliente).get(creado["id_cliente"])
        assert calcular_bandera_naranja(db_session, cliente) is True

    def test_false_si_el_apartado_ya_no_esta_abierto(self, client, auth_headers, db_session):
        """Aunque la fecha esté vencida, un apartado liquidado o cancelado
        no debe encender la bandera -- solo cuenta el que sigue 'abierto'."""
        creado = client.post("/api/v1/clientes", json=_payload_base(), headers=auth_headers).json()
        apartado = _crear_apartado_para_cliente(db_session, creado["id_cliente"])
        _fijar_fecha_apartado(db_session, apartado.id_apartado, date.today() - timedelta(days=60))

        apartado_db = db_session.query(Apartado).get(apartado.id_apartado)
        apartado_db.estatus = EstatusApartado.liquidado
        db_session.commit()

        cliente = db_session.query(Cliente).get(creado["id_cliente"])
        assert calcular_bandera_naranja(db_session, cliente) is False


class TestBanderaNaranjaEndpoint:
    """A través de la API real -- confirma que POST y GET asignan
    bandera_naranja al objeto antes de serializar ClienteRead (ver
    schemas/cliente.py: no es columna mapeada, from_attributes no la
    encuentra si no se asigna a mano antes)."""

    def test_post_nace_con_bandera_naranja_falsa(self, client, auth_headers):
        resp = client.post("/api/v1/clientes", json=_payload_base(), headers=auth_headers)
        assert resp.status_code == 201, resp.text
        assert resp.json()["bandera_naranja"] is False

    def test_get_sin_apartado_bandera_naranja_falsa(self, client, auth_headers):
        creado = client.post("/api/v1/clientes", json=_payload_base(), headers=auth_headers).json()
        resp = client.get(f"/api/v1/clientes/{creado['id_cliente']}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["bandera_naranja"] is False

    def test_get_con_apartado_vencido_bandera_naranja_activa(self, client, auth_headers, db_session):
        creado = client.post("/api/v1/clientes", json=_payload_base(), headers=auth_headers).json()
        apartado = _crear_apartado_para_cliente(db_session, creado["id_cliente"])
        _fijar_fecha_apartado(db_session, apartado.id_apartado, date.today() - timedelta(days=60))

        resp = client.get(f"/api/v1/clientes/{creado['id_cliente']}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["bandera_naranja"] is True


# ---------------------------------------------------------------------------
# 4. Rehabilitar Cliente -- ELIMINADO, no de negocio
# ---------------------------------------------------------------------------
#
# `estatus` es un campo derivado de `saldo`, nunca editable por la
# operadora -- ni por un endpoint de rehabilitación aparte, ni desde
# "Editar Cliente" cuando se construya. `PATCH /clientes/{id}/rehabilitar`
# y `rehabilitar_cliente()` se quitaron del código real por no corresponder
# a ningún caso de negocio del spec real; estos 3 tests se quitan junto con
# ellos, no se dejan como "huecos deliberados" porque no hay nada que
# cubrir. Cuando se construya "Editar Cliente" (UPDATE genérico), su schema
# NO debe exponer `estatus` como campo capturable -- si lo hace, es un bug,
# no una funcionalidad.
