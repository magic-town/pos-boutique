"""
test_clientes.py — mapeado 1:1 a test/casos_clientes.md y a
FULLSTACK/module_clientes.md.

⚠️ SUPUESTOS A VERIFICAR ANTES DE CORRER (ver casos_clientes.md, cabecera):
- Rutas asumidas: POST /api/v1/clientes (confirmada por el usuario),
  GET /api/v1/clientes/{id}, GET /api/v1/clientes?q=,
  PATCH /api/v1/clientes/{id}/rehabilitar (estas 3 últimas INFERIDAS,
  no vistas en app/api/v1/endpoints/clientes.py).
- Fixtures asumidas de conftest.py: `client` (TestClient) y `auth_headers`
  (headers con JWT real), según se describen en test/README.md. Si los
  nombres reales difieren, es un ajuste de los parámetros de cada función.
- `db_session` (usada solo en TestRehabilitarCliente.test_rehabilita_cliente_inactivo
  para forzar `estatus = "inactivo"` sin depender de un endpoint de baja que
  no existe en el spec): NO confirmada en conftest.py — si no existe, hay
  que exponer la sesión de BD de prueba con ese nombre o adaptar el test a
  la que sí exista.
- "Editar Cliente" no se prueba: no existe `editar_cliente` en
  cliente_service.py todavía.

Si algún supuesto no aplica, este archivo falla rápido y explícito (404 en
vez de un assert silencioso) — no está diseñado para "pasar en verde a
ciegas".
"""
import uuid

import pytest


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
        assert data["estatus"] == "activo"
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
# 3. Rehabilitar Cliente
# ---------------------------------------------------------------------------

class TestRehabilitarCliente:

    def test_rehabilita_cliente_inactivo(self, client, auth_headers, db_session):
        # Caso 3.1 — no hay endpoint de "dar de baja" documentado; se fuerza
        # el estado inactivo directo en BD para aislar el caso, igual que
        # hace conftest.cliente_prueba con el bypass ya conocido.
        creado = client.post("/api/v1/clientes", json=_payload_base(), headers=auth_headers).json()
        from app.models.models import Cliente
        cliente_db = db_session.query(Cliente).get(creado["id_cliente"])
        cliente_db.estatus = "inactivo"
        db_session.commit()

        resp = client.patch(f"/api/v1/clientes/{creado['id_cliente']}/rehabilitar", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["estatus"] == "activo"

    def test_rehabilitar_cliente_ya_activo_es_idempotente(self, client, auth_headers):
        # Caso 3.2
        creado = client.post("/api/v1/clientes", json=_payload_base(), headers=auth_headers).json()
        resp = client.patch(f"/api/v1/clientes/{creado['id_cliente']}/rehabilitar", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["estatus"] == "activo"

    def test_rehabilitar_cliente_inexistente(self, client, auth_headers):
        # Caso 3.3 — comportamiento ante None no confirmado contra el endpoint real
        resp = client.patch("/api/v1/clientes/999999/rehabilitar", headers=auth_headers)
        assert resp.status_code == 404
