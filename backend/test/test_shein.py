"""
Tests del módulo Shein — REPORT.md §5 Bloque C, tarea 27.

Cubre: alta de cliente Shein, pedidos (1-4 artículos), artículos agregados
sobre pedido editable, resolución de artículo (confirmar/cancelar ante
variación de precio), corte (autoconfirmación, cascada de cancelación,
agrupación de saldo por cliente), abono (tope de saldo, recálculo de
fecha_pago_programada en sus 4 variantes de frecuencia) y banderas
amarilla/roja.

Convención (ver conftest.py / docs/spec/README.md): un archivo
test_<modulo>.py por módulo. Este comparte `client` / `auth_headers` /
`db_session` de conftest.py -- no los redefine.

No se usa `cliente_prueba` (fixture de `clientes`, no de Shein). Los
helpers `_crear_shein_cliente` / `_crear_shein_pedido` de este archivo
cumplen el mismo rol para `shein_clientes` / `shein_pedidos`, con sufijo
uuid por corrida para no chocar entre tests ni con datos manuales en
pos.db (mismo criterio que `cliente_prueba` en conftest.py).
"""

import uuid
from datetime import date, timedelta

import pytest

from app.models.models import SheinCliente
from app.services import pedido_shein_service as shein_service

BASE = "/api/v1/shein"


# ──────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────

def _crear_shein_cliente(client, auth_headers, **overrides):
    sufijo = uuid.uuid4().hex[:8].upper()
    payload = {
        "nombre": f"Cli Sh {sufijo}",       # <= 20 chars (nombre: String(20))
        "colonia": f"Col{sufijo[:6]}",      # <= 12 chars (colonia: String(12))
        "telefono": 4441234567,
        "frecuencia_pago": "semanal",
        "dia_pago_especifico": None,
        "frecuencia_pago_detalle": None,
    }
    payload.update(overrides)
    resp = client.post(f"{BASE}/clientes", json=payload, headers=auth_headers)
    assert resp.status_code == 201, f"crear_shein_cliente falló: {resp.text}"
    return resp.json()


def _articulo(sku=None, producto="Blusa floral", tipo_producto="Nacional", monto=250.0):
    return {
        "sku": sku or uuid.uuid4().hex[:12].upper(),
        "producto": producto,
        "tipo_producto": tipo_producto,
        "monto": monto,
    }


def _crear_shein_pedido(client, auth_headers, id_shein_cliente, articulos=None):
    payload = {
        "id_shein_cliente": id_shein_cliente,
        "articulos": articulos or [_articulo()],
    }
    resp = client.post(f"{BASE}/pedidos", json=payload, headers=auth_headers)
    assert resp.status_code == 201, f"crear_shein_pedido falló: {resp.text}"
    return resp.json()


def _resolver_articulo(client, auth_headers, id_shein_articulo, estatus_articulo, monto_vigente=None):
    payload = {"estatus_articulo": estatus_articulo}
    if monto_vigente is not None:
        payload["monto_vigente"] = monto_vigente
    return client.patch(
        f"{BASE}/pedidos/articulos/{id_shein_articulo}", json=payload, headers=auth_headers
    )


def _registrar_corte(client, auth_headers, id_shein_pedidos, total_ticket, fecha_corte=None):
    payload = {
        "fecha_corte": (fecha_corte or date.today()).isoformat(),
        "id_shein_pedidos": id_shein_pedidos,
        "total_ticket": total_ticket,
    }
    return client.post(f"{BASE}/cortes", json=payload, headers=auth_headers)


def _registrar_abono(client, auth_headers, id_shein_cliente, monto, forma_pago="efectivo"):
    payload = {"id_shein_cliente": id_shein_cliente, "monto": monto, "forma_pago": forma_pago}
    return client.post(f"{BASE}/abono", json=payload, headers=auth_headers)


def _congelar_hoy(monkeypatch, fecha_fija: date):
    """Fija date.today() dentro de pedido_shein_service, para probar las 4
    fórmulas de fecha_pago_programada sin depender de la fecha real de
    ejecución (necesario para casos límite: fin de mes, día 31, etc.)."""

    class _FechaFija(date):
        @classmethod
        def today(cls):
            return fecha_fija

    monkeypatch.setattr(shein_service, "date", _FechaFija)


# ──────────────────────────────────────────────────────────────────────────
# Cliente Shein
# ──────────────────────────────────────────────────────────────────────────

class TestClienteShein:

    def test_crear_cliente_defaults(self, client, auth_headers):
        cliente = _crear_shein_cliente(client, auth_headers)
        assert cliente["saldo"] == 0
        assert cliente["estatus"] == "inactivo"
        assert cliente["fecha_pago_programada"] is None
        assert cliente["bandera"] is None

    def test_crear_cliente_dia_especifico_sin_dia_rechazado(self, client, auth_headers):
        resp = client.post(
            f"{BASE}/clientes",
            json={
                "nombre": "Cliente X", "colonia": "Centro", "telefono": 4441111111,
                "frecuencia_pago": "dia_especifico_mes",
                "dia_pago_especifico": None, "frecuencia_pago_detalle": None,
            },
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_crear_cliente_otro_sin_detalle_rechazado(self, client, auth_headers):
        resp = client.post(
            f"{BASE}/clientes",
            json={
                "nombre": "Cliente X", "colonia": "Centro", "telefono": 4441111111,
                "frecuencia_pago": "otro",
                "dia_pago_especifico": None, "frecuencia_pago_detalle": None,
            },
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_crear_cliente_telefono_invalido_rechazado(self, client, auth_headers):
        resp = client.post(
            f"{BASE}/clientes",
            json={
                "nombre": "Cliente X", "colonia": "Centro", "telefono": 123,
                "frecuencia_pago": "semanal",
                "dia_pago_especifico": None, "frecuencia_pago_detalle": None,
            },
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_crear_cliente_nombre_vacio_rechazado(self, client, auth_headers):
        resp = client.post(
            f"{BASE}/clientes",
            json={
                "nombre": "   ", "colonia": "Centro", "telefono": 4441111111,
                "frecuencia_pago": "semanal",
                "dia_pago_especifico": None, "frecuencia_pago_detalle": None,
            },
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_listar_clientes_incluye_creado(self, client, auth_headers):
        cliente = _crear_shein_cliente(client, auth_headers)
        resp = client.get(f"{BASE}/clientes", headers=auth_headers)
        assert resp.status_code == 200
        ids = [c["id_shein_cliente"] for c in resp.json()]
        assert cliente["id_shein_cliente"] in ids

    def test_independiente_de_clientes_no_fk(self, client, auth_headers):
        """module_shein.md regla 1: shein_clientes no tiene FK a clientes.
        No hay endpoint que exija id_cliente al crear un shein_cliente."""
        cliente = _crear_shein_cliente(client, auth_headers)
        assert "id_cliente" not in cliente


# ──────────────────────────────────────────────────────────────────────────
# Pedido Shein
# ──────────────────────────────────────────────────────────────────────────

class TestPedidoShein:

    def test_crear_pedido_1_articulo(self, client, auth_headers):
        cliente = _crear_shein_cliente(client, auth_headers)
        pedido = _crear_shein_pedido(client, auth_headers, cliente["id_shein_cliente"])
        assert len(pedido["articulos"]) == 1
        assert pedido["id_shein_corte"] is None
        assert pedido["estatus_pago"] is None

    def test_crear_pedido_4_articulos(self, client, auth_headers):
        cliente = _crear_shein_cliente(client, auth_headers)
        articulos = [_articulo(monto=100 + i) for i in range(4)]
        pedido = _crear_shein_pedido(client, auth_headers, cliente["id_shein_cliente"], articulos)
        assert len(pedido["articulos"]) == 4

    def test_crear_pedido_5_articulos_rechazado(self, client, auth_headers):
        cliente = _crear_shein_cliente(client, auth_headers)
        articulos = [_articulo(monto=100 + i) for i in range(5)]
        resp = client.post(
            f"{BASE}/pedidos",
            json={"id_shein_cliente": cliente["id_shein_cliente"], "articulos": articulos},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_crear_pedido_0_articulos_rechazado(self, client, auth_headers):
        cliente = _crear_shein_cliente(client, auth_headers)
        resp = client.post(
            f"{BASE}/pedidos",
            json={"id_shein_cliente": cliente["id_shein_cliente"], "articulos": []},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_crear_pedido_cliente_inexistente(self, client, auth_headers):
        resp = client.post(
            f"{BASE}/pedidos",
            json={"id_shein_cliente": 999999, "articulos": [_articulo()]},
            headers=auth_headers,
        )
        assert resp.status_code == 404

    def test_crear_pedido_sku_obligatorio(self, client, auth_headers):
        """module_shein.md: sku obligatorio en cada renglón."""
        cliente = _crear_shein_cliente(client, auth_headers)
        articulo = _articulo()
        articulo.pop("sku")
        resp = client.post(
            f"{BASE}/pedidos",
            json={"id_shein_cliente": cliente["id_shein_cliente"], "articulos": [articulo]},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_monto_pedido_antes_del_corte_es_cero(self, client, auth_headers):
        """monto_pedido solo suma artículos 'confirmado' (regla 8 /
        _monto_pedido en el service) -- antes del corte todo está
        'vigente', así que monto_pedido debe ser 0 aunque monto_pedido_vigente
        refleje el monto capturado."""
        cliente = _crear_shein_cliente(client, auth_headers)
        pedido = _crear_shein_pedido(
            client, auth_headers, cliente["id_shein_cliente"], [_articulo(monto=300.0)]
        )
        assert pedido["monto_pedido"] == 0
        assert pedido["monto_pedido_vigente"] == 300.0

    def test_listar_pedidos_filtro_sin_corte(self, client, auth_headers):
        cliente = _crear_shein_cliente(client, auth_headers)
        pedido = _crear_shein_pedido(client, auth_headers, cliente["id_shein_cliente"])
        resp = client.get(f"{BASE}/pedidos", params={"sin_corte": True}, headers=auth_headers)
        assert resp.status_code == 200
        ids = [p["id_shein_pedido"] for p in resp.json()]
        assert pedido["id_shein_pedido"] in ids

    def test_listar_pedidos_filtro_por_cliente(self, client, auth_headers):
        cliente_a = _crear_shein_cliente(client, auth_headers)
        cliente_b = _crear_shein_cliente(client, auth_headers)
        pedido_a = _crear_shein_pedido(client, auth_headers, cliente_a["id_shein_cliente"])
        _crear_shein_pedido(client, auth_headers, cliente_b["id_shein_cliente"])
        resp = client.get(
            f"{BASE}/pedidos",
            params={"id_shein_cliente": cliente_a["id_shein_cliente"]},
            headers=auth_headers,
        )
        ids = [p["id_shein_pedido"] for p in resp.json()]
        assert pedido_a["id_shein_pedido"] in ids
        assert all(p["id_shein_cliente"] == cliente_a["id_shein_cliente"] for p in resp.json())


# ──────────────────────────────────────────────────────────────────────────
# Artículo Shein — agregar / resolver estatus
# ──────────────────────────────────────────────────────────────────────────

class TestArticuloShein:

    def test_agregar_articulo_pedido_editable(self, client, auth_headers):
        cliente = _crear_shein_cliente(client, auth_headers)
        pedido = _crear_shein_pedido(client, auth_headers, cliente["id_shein_cliente"])
        resp = client.post(
            f"{BASE}/pedidos/{pedido['id_shein_pedido']}/articulos",
            json=_articulo(),
            headers=auth_headers,
        )
        assert resp.status_code == 201
        assert len(resp.json()["articulos"]) == 2

    def test_agregar_articulo_limite_4_rechazado(self, client, auth_headers):
        cliente = _crear_shein_cliente(client, auth_headers)
        articulos = [_articulo(monto=100 + i) for i in range(4)]
        pedido = _crear_shein_pedido(client, auth_headers, cliente["id_shein_cliente"], articulos)
        resp = client.post(
            f"{BASE}/pedidos/{pedido['id_shein_pedido']}/articulos",
            json=_articulo(),
            headers=auth_headers,
        )
        assert resp.status_code == 409

    def test_agregar_articulo_pedido_ya_cortado_rechazado(self, client, auth_headers):
        cliente = _crear_shein_cliente(client, auth_headers)
        pedido = _crear_shein_pedido(client, auth_headers, cliente["id_shein_cliente"])
        corte = _registrar_corte(client, auth_headers, [pedido["id_shein_pedido"]], total_ticket=100)
        assert corte.status_code == 201

        resp = client.post(
            f"{BASE}/pedidos/{pedido['id_shein_pedido']}/articulos",
            json=_articulo(),
            headers=auth_headers,
        )
        assert resp.status_code == 409

    def test_agregar_articulo_pedido_inexistente(self, client, auth_headers):
        resp = client.post(
            f"{BASE}/pedidos/999999/articulos", json=_articulo(), headers=auth_headers
        )
        assert resp.status_code == 404

    def test_confirmar_articulo_manual(self, client, auth_headers):
        cliente = _crear_shein_cliente(client, auth_headers)
        pedido = _crear_shein_pedido(client, auth_headers, cliente["id_shein_cliente"])
        id_articulo = pedido["articulos"][0]["id_shein_articulo"]
        resp = _resolver_articulo(client, auth_headers, id_articulo, "confirmado", monto_vigente=350.0)
        assert resp.status_code == 200
        body = resp.json()
        assert body["estatus_articulo"] == "confirmado"
        assert body["monto_vigente"] == 350.0

    def test_cancelar_articulo_manual(self, client, auth_headers):
        cliente = _crear_shein_cliente(client, auth_headers)
        pedido = _crear_shein_pedido(client, auth_headers, cliente["id_shein_cliente"])
        id_articulo = pedido["articulos"][0]["id_shein_articulo"]
        resp = _resolver_articulo(client, auth_headers, id_articulo, "cancelado")
        assert resp.status_code == 200
        assert resp.json()["estatus_articulo"] == "cancelado"

    def test_resolver_articulo_monto_vigente_negativo_rechazado(self, client, auth_headers):
        cliente = _crear_shein_cliente(client, auth_headers)
        pedido = _crear_shein_pedido(client, auth_headers, cliente["id_shein_cliente"])
        id_articulo = pedido["articulos"][0]["id_shein_articulo"]
        resp = _resolver_articulo(client, auth_headers, id_articulo, "confirmado", monto_vigente=-5.0)
        assert resp.status_code == 422

    def test_resolver_articulo_pedido_ya_cortado_rechazado(self, client, auth_headers):
        cliente = _crear_shein_cliente(client, auth_headers)
        pedido = _crear_shein_pedido(client, auth_headers, cliente["id_shein_cliente"])
        id_articulo = pedido["articulos"][0]["id_shein_articulo"]
        corte = _registrar_corte(client, auth_headers, [pedido["id_shein_pedido"]], total_ticket=100)
        assert corte.status_code == 201

        resp = _resolver_articulo(client, auth_headers, id_articulo, "cancelado")
        assert resp.status_code == 409

    def test_resolver_articulo_inexistente(self, client, auth_headers):
        resp = _resolver_articulo(client, auth_headers, 999999, "confirmado")
        assert resp.status_code == 404


# ──────────────────────────────────────────────────────────────────────────
# Corte Shein
# ──────────────────────────────────────────────────────────────────────────

class TestCorteShein:

    def test_corte_sin_cambio_precio_autoconfirma_y_carga_saldo(self, client, auth_headers):
        cliente = _crear_shein_cliente(client, auth_headers)
        pedido = _crear_shein_pedido(
            client, auth_headers, cliente["id_shein_cliente"], [_articulo(monto=500.0)]
        )
        resp = _registrar_corte(client, auth_headers, [pedido["id_shein_pedido"]], total_ticket=450.0)
        assert resp.status_code == 201
        corte = resp.json()
        assert corte["total_pedidos"] == 1
        assert corte["suma_pedidos"] == 500.0
        assert corte["cupon"] == pytest.approx(50.0)

        clientes = client.get(f"{BASE}/clientes", headers=auth_headers).json()
        actualizado = next(c for c in clientes if c["id_shein_cliente"] == cliente["id_shein_cliente"])
        assert actualizado["saldo"] == 500.0
        assert actualizado["estatus"] == "activo"

        pedidos = client.get(
            f"{BASE}/pedidos", params={"id_shein_cliente": cliente["id_shein_cliente"]},
            headers=auth_headers,
        ).json()
        actualizado_pedido = next(p for p in pedidos if p["id_shein_pedido"] == pedido["id_shein_pedido"])
        assert actualizado_pedido["id_shein_corte"] == corte["id_shein_corte"]
        assert actualizado_pedido["estatus_pago"] == "pago_pendiente"
        assert actualizado_pedido["monto_pedido"] == 500.0

    def test_corte_confirmado_manual_usa_monto_vigente(self, client, auth_headers):
        cliente = _crear_shein_cliente(client, auth_headers)
        pedido = _crear_shein_pedido(
            client, auth_headers, cliente["id_shein_cliente"], [_articulo(monto=200.0)]
        )
        id_articulo = pedido["articulos"][0]["id_shein_articulo"]
        _resolver_articulo(client, auth_headers, id_articulo, "confirmado", monto_vigente=260.0)

        resp = _registrar_corte(client, auth_headers, [pedido["id_shein_pedido"]], total_ticket=250.0)
        assert resp.status_code == 201
        assert resp.json()["suma_pedidos"] == 260.0

    def test_corte_cascada_cancelacion_total(self, client, auth_headers):
        """module_shein.md regla 9: si todos los artículos quedan cancelados,
        el pedido no recibe id_shein_corte ni estatus_pago, y el saldo del
        cliente no se afecta."""
        cliente = _crear_shein_cliente(client, auth_headers)
        pedido = _crear_shein_pedido(
            client, auth_headers, cliente["id_shein_cliente"],
            [_articulo(monto=100.0), _articulo(monto=200.0)],
        )
        for articulo in pedido["articulos"]:
            resp = _resolver_articulo(client, auth_headers, articulo["id_shein_articulo"], "cancelado")
            assert resp.status_code == 200

        resp = _registrar_corte(client, auth_headers, [pedido["id_shein_pedido"]], total_ticket=1.0)
        assert resp.status_code == 201
        corte = resp.json()
        assert corte["total_pedidos"] == 0
        assert corte["suma_pedidos"] == 0

        pedidos = client.get(
            f"{BASE}/pedidos", params={"sin_corte": True}, headers=auth_headers
        ).json()
        ids = [p["id_shein_pedido"] for p in pedidos]
        assert pedido["id_shein_pedido"] in ids, (
            "El pedido totalmente cancelado debería seguir sin id_shein_corte "
            "(no fue vinculado al corte) y por lo tanto seguir apareciendo "
            "bajo el filtro sin_corte."
        )

        clientes = client.get(f"{BASE}/clientes", headers=auth_headers).json()
        actualizado = next(c for c in clientes if c["id_shein_cliente"] == cliente["id_shein_cliente"])
        assert actualizado["saldo"] == 0
        assert actualizado["estatus"] == "inactivo"

    def test_corte_pedido_totalmente_cancelado_puede_reenviarse_sin_recargo(self, client, auth_headers):
        """Efecto colateral de la cascada anterior: como el pedido nunca
        recibe id_shein_corte, la validación 'ya_en_corte' no lo bloquea y
        puede reenviarse a un segundo corte. Verifica que esto sea inocuo
        (no duplica cargo) y no que sea deseable -- documenta el
        comportamiento actual para que no sorprenda en producción."""
        cliente = _crear_shein_cliente(client, auth_headers)
        pedido = _crear_shein_pedido(
            client, auth_headers, cliente["id_shein_cliente"], [_articulo(monto=150.0)]
        )
        _resolver_articulo(client, auth_headers, pedido["articulos"][0]["id_shein_articulo"], "cancelado")

        primer = _registrar_corte(client, auth_headers, [pedido["id_shein_pedido"]], total_ticket=1.0)
        assert primer.status_code == 201
        segundo = _registrar_corte(client, auth_headers, [pedido["id_shein_pedido"]], total_ticket=1.0)
        assert segundo.status_code == 201  # no 409: el pedido nunca quedó "en corte"

        clientes = client.get(f"{BASE}/clientes", headers=auth_headers).json()
        actualizado = next(c for c in clientes if c["id_shein_cliente"] == cliente["id_shein_cliente"])
        assert actualizado["saldo"] == 0, "No debe cargarse saldo por un pedido sin artículos confirmados."

    def test_corte_parcial_solo_confirmados_cuentan(self, client, auth_headers):
        cliente = _crear_shein_cliente(client, auth_headers)
        pedido = _crear_shein_pedido(
            client, auth_headers, cliente["id_shein_cliente"],
            [_articulo(monto=100.0), _articulo(monto=400.0)],
        )
        articulos = pedido["articulos"]
        _resolver_articulo(client, auth_headers, articulos[0]["id_shein_articulo"], "cancelado")
        # el segundo se deja 'vigente' -> se autoconfirma sin cambio de precio

        resp = _registrar_corte(client, auth_headers, [pedido["id_shein_pedido"]], total_ticket=350.0)
        assert resp.status_code == 201
        assert resp.json()["suma_pedidos"] == 400.0

    def test_corte_agrupa_saldo_multiples_pedidos_mismo_cliente(self, client, auth_headers):
        cliente = _crear_shein_cliente(client, auth_headers)
        pedido_1 = _crear_shein_pedido(
            client, auth_headers, cliente["id_shein_cliente"], [_articulo(monto=100.0)]
        )
        pedido_2 = _crear_shein_pedido(
            client, auth_headers, cliente["id_shein_cliente"], [_articulo(monto=250.0)]
        )
        resp = _registrar_corte(
            client, auth_headers,
            [pedido_1["id_shein_pedido"], pedido_2["id_shein_pedido"]],
            total_ticket=300.0,
        )
        assert resp.status_code == 201
        corte = resp.json()
        assert corte["total_pedidos"] == 2
        assert corte["suma_pedidos"] == 350.0

        clientes = client.get(f"{BASE}/clientes", headers=auth_headers).json()
        actualizado = next(c for c in clientes if c["id_shein_cliente"] == cliente["id_shein_cliente"])
        assert actualizado["saldo"] == 350.0, "El saldo debe cargarse una sola vez con la suma, no duplicarse por pedido."

    def test_corte_multiples_clientes_no_mezcla_saldos(self, client, auth_headers):
        cliente_a = _crear_shein_cliente(client, auth_headers)
        cliente_b = _crear_shein_cliente(client, auth_headers)
        pedido_a = _crear_shein_pedido(
            client, auth_headers, cliente_a["id_shein_cliente"], [_articulo(monto=120.0)]
        )
        pedido_b = _crear_shein_pedido(
            client, auth_headers, cliente_b["id_shein_cliente"], [_articulo(monto=80.0)]
        )
        resp = _registrar_corte(
            client, auth_headers, [pedido_a["id_shein_pedido"], pedido_b["id_shein_pedido"]],
            total_ticket=180.0,
        )
        assert resp.status_code == 201

        clientes = {c["id_shein_cliente"]: c for c in client.get(f"{BASE}/clientes", headers=auth_headers).json()}
        assert clientes[cliente_a["id_shein_cliente"]]["saldo"] == 120.0
        assert clientes[cliente_b["id_shein_cliente"]]["saldo"] == 80.0

    def test_corte_pedido_ya_incluido_rechazado(self, client, auth_headers):
        cliente = _crear_shein_cliente(client, auth_headers)
        pedido = _crear_shein_pedido(client, auth_headers, cliente["id_shein_cliente"])
        primer = _registrar_corte(client, auth_headers, [pedido["id_shein_pedido"]], total_ticket=100.0)
        assert primer.status_code == 201

        segundo = _registrar_corte(client, auth_headers, [pedido["id_shein_pedido"]], total_ticket=100.0)
        assert segundo.status_code == 409

    def test_corte_pedido_inexistente_rechazado(self, client, auth_headers):
        resp = _registrar_corte(client, auth_headers, [999999], total_ticket=100.0)
        assert resp.status_code == 404

    def test_corte_lista_mixta_encontrados_y_faltantes_prioriza_404(self, client, auth_headers):
        cliente = _crear_shein_cliente(client, auth_headers)
        pedido = _crear_shein_pedido(client, auth_headers, cliente["id_shein_cliente"])
        resp = _registrar_corte(
            client, auth_headers, [pedido["id_shein_pedido"], 999999], total_ticket=100.0
        )
        assert resp.status_code == 404

    def test_corte_total_ticket_no_positivo_rechazado(self, client, auth_headers):
        cliente = _crear_shein_cliente(client, auth_headers)
        pedido = _crear_shein_pedido(client, auth_headers, cliente["id_shein_cliente"])
        resp = _registrar_corte(client, auth_headers, [pedido["id_shein_pedido"]], total_ticket=0)
        assert resp.status_code == 422

    def test_corte_lista_pedidos_vacia_rechazada(self, client, auth_headers):
        resp = client.post(
            f"{BASE}/cortes",
            json={"fecha_corte": date.today().isoformat(), "id_shein_pedidos": [], "total_ticket": 100.0},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_corte_cupon_puede_ser_negativo(self, client, auth_headers):
        """cupon = suma_pedidos - total_ticket. No hay validación que impida
        total_ticket > suma_pedidos, así que cupon puede salir negativo --
        confirma que el backend no lo bloquea silenciosamente."""
        cliente = _crear_shein_cliente(client, auth_headers)
        pedido = _crear_shein_pedido(
            client, auth_headers, cliente["id_shein_cliente"], [_articulo(monto=100.0)]
        )
        resp = _registrar_corte(client, auth_headers, [pedido["id_shein_pedido"]], total_ticket=150.0)
        assert resp.status_code == 201
        assert resp.json()["cupon"] == pytest.approx(-50.0)


# ──────────────────────────────────────────────────────────────────────────
# Consulta de Cortes
# ──────────────────────────────────────────────────────────────────────────

class TestConsultaCortes:

    def test_listar_cortes_incluye_creado(self, client, auth_headers):
        cliente = _crear_shein_cliente(client, auth_headers)
        pedido = _crear_shein_pedido(client, auth_headers, cliente["id_shein_cliente"])
        corte = _registrar_corte(client, auth_headers, [pedido["id_shein_pedido"]], total_ticket=100.0).json()

        resp = client.get(f"{BASE}/cortes", headers=auth_headers)
        assert resp.status_code == 200
        ids = [c["id_shein_corte"] for c in resp.json()]
        assert corte["id_shein_corte"] in ids

    def test_detalle_corte(self, client, auth_headers):
        cliente = _crear_shein_cliente(client, auth_headers)
        pedido = _crear_shein_pedido(client, auth_headers, cliente["id_shein_cliente"])
        corte = _registrar_corte(client, auth_headers, [pedido["id_shein_pedido"]], total_ticket=100.0).json()

        resp = client.get(f"{BASE}/cortes/{corte['id_shein_corte']}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["id_shein_corte"] == corte["id_shein_corte"]

    def test_detalle_corte_inexistente(self, client, auth_headers):
        resp = client.get(f"{BASE}/cortes/999999", headers=auth_headers)
        assert resp.status_code == 404


# ──────────────────────────────────────────────────────────────────────────
# Abono Shein
# ──────────────────────────────────────────────────────────────────────────

class TestAbonoShein:

    def _cliente_con_saldo(self, client, auth_headers, saldo, **overrides):
        cliente = _crear_shein_cliente(client, auth_headers, **overrides)
        pedido = _crear_shein_pedido(
            client, auth_headers, cliente["id_shein_cliente"], [_articulo(monto=saldo)]
        )
        corte = _registrar_corte(client, auth_headers, [pedido["id_shein_pedido"]], total_ticket=1.0)
        assert corte.status_code == 201
        return cliente["id_shein_cliente"]

    def test_abono_reduce_saldo(self, client, auth_headers):
        id_cliente = self._cliente_con_saldo(client, auth_headers, saldo=500.0)
        resp = _registrar_abono(client, auth_headers, id_cliente, monto=200.0)
        assert resp.status_code == 201
        body = resp.json()
        assert body["saldo_resultante"] == 300.0

        clientes = client.get(f"{BASE}/clientes", headers=auth_headers).json()
        actualizado = next(c for c in clientes if c["id_shein_cliente"] == id_cliente)
        assert actualizado["saldo"] == 300.0
        assert actualizado["estatus"] == "activo"

    def test_abono_no_puede_exceder_saldo(self, client, auth_headers):
        id_cliente = self._cliente_con_saldo(client, auth_headers, saldo=100.0)
        resp = _registrar_abono(client, auth_headers, id_cliente, monto=150.0)
        assert resp.status_code == 409

    def test_abono_monto_no_positivo_rechazado(self, client, auth_headers):
        id_cliente = self._cliente_con_saldo(client, auth_headers, saldo=100.0)
        resp = _registrar_abono(client, auth_headers, id_cliente, monto=0)
        assert resp.status_code == 422

    def test_abono_liquida_saldo_a_cero_vuelve_inactivo(self, client, auth_headers):
        id_cliente = self._cliente_con_saldo(client, auth_headers, saldo=250.0)
        resp = _registrar_abono(client, auth_headers, id_cliente, monto=250.0)
        assert resp.status_code == 201

        clientes = client.get(f"{BASE}/clientes", headers=auth_headers).json()
        actualizado = next(c for c in clientes if c["id_shein_cliente"] == id_cliente)
        assert actualizado["saldo"] == 0
        assert actualizado["estatus"] == "inactivo"

    def test_abono_cliente_inexistente(self, client, auth_headers):
        resp = _registrar_abono(client, auth_headers, 999999, monto=100.0)
        assert resp.status_code == 404

    def test_abono_registra_movimiento_con_forma_pago(self, client, auth_headers):
        id_cliente = self._cliente_con_saldo(client, auth_headers, saldo=100.0)
        resp = _registrar_abono(client, auth_headers, id_cliente, monto=40.0, forma_pago="transferencia")
        assert resp.status_code == 201
        assert resp.json()["forma_pago"] == "transferencia"

    # ── fecha_pago_programada: 4 fórmulas de frecuencia (§6 regla 5, reutiliza
    #    la lógica de clientes §2 regla 4) ──────────────────────────────────

    def test_abono_frecuencia_semanal_suma_7_dias(self, client, auth_headers, monkeypatch):
        hoy = date(2026, 7, 6)  # lunes
        _congelar_hoy(monkeypatch, hoy)
        id_cliente = self._cliente_con_saldo(client, auth_headers, saldo=100.0, frecuencia_pago="semanal")
        resp = _registrar_abono(client, auth_headers, id_cliente, monto=10.0)
        assert resp.status_code == 201

        clientes = client.get(f"{BASE}/clientes", headers=auth_headers).json()
        actualizado = next(c for c in clientes if c["id_shein_cliente"] == id_cliente)
        assert actualizado["fecha_pago_programada"] == (hoy + timedelta(days=7)).isoformat()

    def test_abono_frecuencia_quincenal_elige_dia_15_si_es_posterior(self, client, auth_headers, monkeypatch):
        hoy = date(2026, 7, 3)
        _congelar_hoy(monkeypatch, hoy)
        id_cliente = self._cliente_con_saldo(client, auth_headers, saldo=100.0, frecuencia_pago="quincenal")
        _registrar_abono(client, auth_headers, id_cliente, monto=10.0)

        clientes = client.get(f"{BASE}/clientes", headers=auth_headers).json()
        actualizado = next(c for c in clientes if c["id_shein_cliente"] == id_cliente)
        assert actualizado["fecha_pago_programada"] == "2026-07-15"

    def test_abono_frecuencia_quincenal_despues_del_15_usa_fin_de_mes(self, client, auth_headers, monkeypatch):
        hoy = date(2026, 7, 20)
        _congelar_hoy(monkeypatch, hoy)
        id_cliente = self._cliente_con_saldo(client, auth_headers, saldo=100.0, frecuencia_pago="quincenal")
        _registrar_abono(client, auth_headers, id_cliente, monto=10.0)

        clientes = client.get(f"{BASE}/clientes", headers=auth_headers).json()
        actualizado = next(c for c in clientes if c["id_shein_cliente"] == id_cliente)
        assert actualizado["fecha_pago_programada"] == "2026-07-31"

    def test_abono_frecuencia_quincenal_despues_de_fin_de_mes_salta_a_15_siguiente(self, client, auth_headers, monkeypatch):
        hoy = date(2026, 7, 31)
        _congelar_hoy(monkeypatch, hoy)
        id_cliente = self._cliente_con_saldo(client, auth_headers, saldo=100.0, frecuencia_pago="quincenal")
        _registrar_abono(client, auth_headers, id_cliente, monto=10.0)

        clientes = client.get(f"{BASE}/clientes", headers=auth_headers).json()
        actualizado = next(c for c in clientes if c["id_shein_cliente"] == id_cliente)
        assert actualizado["fecha_pago_programada"] == "2026-08-15"

    def test_abono_frecuencia_dia_especifico_dentro_del_mes(self, client, auth_headers, monkeypatch):
        hoy = date(2026, 7, 5)
        _congelar_hoy(monkeypatch, hoy)
        id_cliente = self._cliente_con_saldo(
            client, auth_headers, saldo=100.0,
            frecuencia_pago="dia_especifico_mes", dia_pago_especifico=20,
        )
        _registrar_abono(client, auth_headers, id_cliente, monto=10.0)

        clientes = client.get(f"{BASE}/clientes", headers=auth_headers).json()
        actualizado = next(c for c in clientes if c["id_shein_cliente"] == id_cliente)
        assert actualizado["fecha_pago_programada"] == "2026-07-20"

    def test_abono_frecuencia_dia_especifico_ya_paso_salta_al_mes_siguiente(self, client, auth_headers, monkeypatch):
        hoy = date(2026, 7, 25)
        _congelar_hoy(monkeypatch, hoy)
        id_cliente = self._cliente_con_saldo(
            client, auth_headers, saldo=100.0,
            frecuencia_pago="dia_especifico_mes", dia_pago_especifico=20,
        )
        _registrar_abono(client, auth_headers, id_cliente, monto=10.0)

        clientes = client.get(f"{BASE}/clientes", headers=auth_headers).json()
        actualizado = next(c for c in clientes if c["id_shein_cliente"] == id_cliente)
        assert actualizado["fecha_pago_programada"] == "2026-08-20"

    def test_abono_frecuencia_dia_especifico_clamped_en_febrero(self, client, auth_headers, monkeypatch):
        """dia_pago_especifico=31: en enero el día 31 sí existe, así que
        hoy debe fijarse en 2026-01-31 mismo (no antes) para que
        `candidato_este_mes > fecha_abono` sea falso y la fórmula se vea
        forzada a saltar a febrero, donde sí debe recortarse (clamp) al
        último día real del mes (28, 2026 no es bisiesto) en vez de
        reventar con un ValueError por 'day 31 out of range'."""
        hoy = date(2026, 1, 31)
        _congelar_hoy(monkeypatch, hoy)
        id_cliente = self._cliente_con_saldo(
            client, auth_headers, saldo=100.0,
            frecuencia_pago="dia_especifico_mes", dia_pago_especifico=31,
        )
        _registrar_abono(client, auth_headers, id_cliente, monto=10.0)

        clientes = client.get(f"{BASE}/clientes", headers=auth_headers).json()
        actualizado = next(c for c in clientes if c["id_shein_cliente"] == id_cliente)
        assert actualizado["fecha_pago_programada"] == "2026-02-28"

    def test_abono_frecuencia_dia_especifico_31_en_enero_no_salta_mes(self, client, auth_headers, monkeypatch):
        """Caso contrastante al anterior: si hoy es anterior al día 31 y el
        mes actual sí tiene 31 días, la fecha programada debe quedarse en
        el mismo mes -- no debe saltarse de largo a febrero."""
        hoy = date(2026, 1, 25)
        _congelar_hoy(monkeypatch, hoy)
        id_cliente = self._cliente_con_saldo(
            client, auth_headers, saldo=100.0,
            frecuencia_pago="dia_especifico_mes", dia_pago_especifico=31,
        )
        _registrar_abono(client, auth_headers, id_cliente, monto=10.0)

        clientes = client.get(f"{BASE}/clientes", headers=auth_headers).json()
        actualizado = next(c for c in clientes if c["id_shein_cliente"] == id_cliente)
        assert actualizado["fecha_pago_programada"] == "2026-01-31"

    def test_abono_frecuencia_otro_nunca_calcula_fecha(self, client, auth_headers):
        id_cliente = self._cliente_con_saldo(
            client, auth_headers, saldo=100.0,
            frecuencia_pago="otro", frecuencia_pago_detalle="Cada visita a la tienda",
        )
        resp = _registrar_abono(client, auth_headers, id_cliente, monto=10.0)
        assert resp.status_code == 201

        clientes = client.get(f"{BASE}/clientes", headers=auth_headers).json()
        actualizado = next(c for c in clientes if c["id_shein_cliente"] == id_cliente)
        assert actualizado["fecha_pago_programada"] is None

    def test_abono_recalcula_en_cada_abono_subsiguiente(self, client, auth_headers, monkeypatch):
        _congelar_hoy(monkeypatch, date(2026, 7, 1))
        id_cliente = self._cliente_con_saldo(client, auth_headers, saldo=100.0, frecuencia_pago="semanal")
        _registrar_abono(client, auth_headers, id_cliente, monto=10.0)

        _congelar_hoy(monkeypatch, date(2026, 7, 10))
        _registrar_abono(client, auth_headers, id_cliente, monto=10.0)

        clientes = client.get(f"{BASE}/clientes", headers=auth_headers).json()
        actualizado = next(c for c in clientes if c["id_shein_cliente"] == id_cliente)
        assert actualizado["fecha_pago_programada"] == "2026-07-17"


# ──────────────────────────────────────────────────────────────────────────
# Banderas — amarilla / roja (calculadas al vuelo, no persistidas)
# ──────────────────────────────────────────────────────────────────────────

class TestBanderaShein:

    def _set_estado(self, db_session, id_shein_cliente, saldo, fecha_pago_programada):
        cliente = db_session.query(SheinCliente).get(id_shein_cliente)
        cliente.saldo = saldo
        cliente.fecha_pago_programada = fecha_pago_programada
        db_session.commit()

    def test_sin_deuda_sin_bandera(self, client, auth_headers, db_session):
        cliente = _crear_shein_cliente(client, auth_headers)
        self._set_estado(db_session, cliente["id_shein_cliente"], saldo=0, fecha_pago_programada=None)

        clientes = client.get(f"{BASE}/clientes", headers=auth_headers).json()
        actualizado = next(c for c in clientes if c["id_shein_cliente"] == cliente["id_shein_cliente"])
        assert actualizado["bandera"] is None

    def test_fecha_lejana_sin_bandera(self, client, auth_headers, db_session):
        cliente = _crear_shein_cliente(client, auth_headers)
        self._set_estado(
            db_session, cliente["id_shein_cliente"], saldo=100.0,
            fecha_pago_programada=date.today() + timedelta(days=10),
        )
        clientes = client.get(f"{BASE}/clientes", headers=auth_headers).json()
        actualizado = next(c for c in clientes if c["id_shein_cliente"] == cliente["id_shein_cliente"])
        assert actualizado["bandera"] is None

    def test_bandera_amarilla_dentro_de_2_dias(self, client, auth_headers, db_session):
        cliente = _crear_shein_cliente(client, auth_headers)
        self._set_estado(
            db_session, cliente["id_shein_cliente"], saldo=100.0,
            fecha_pago_programada=date.today() + timedelta(days=2),
        )
        clientes = client.get(f"{BASE}/clientes", headers=auth_headers).json()
        actualizado = next(c for c in clientes if c["id_shein_cliente"] == cliente["id_shein_cliente"])
        assert actualizado["bandera"] == "amarilla"

    def test_bandera_amarilla_hoy_mismo(self, client, auth_headers, db_session):
        cliente = _crear_shein_cliente(client, auth_headers)
        self._set_estado(
            db_session, cliente["id_shein_cliente"], saldo=100.0,
            fecha_pago_programada=date.today(),
        )
        clientes = client.get(f"{BASE}/clientes", headers=auth_headers).json()
        actualizado = next(c for c in clientes if c["id_shein_cliente"] == cliente["id_shein_cliente"])
        assert actualizado["bandera"] == "amarilla"

    def test_bandera_roja_vencida(self, client, auth_headers, db_session):
        cliente = _crear_shein_cliente(client, auth_headers)
        self._set_estado(
            db_session, cliente["id_shein_cliente"], saldo=100.0,
            fecha_pago_programada=date.today() - timedelta(days=1),
        )
        clientes = client.get(f"{BASE}/clientes", headers=auth_headers).json()
        actualizado = next(c for c in clientes if c["id_shein_cliente"] == cliente["id_shein_cliente"])
        assert actualizado["bandera"] == "roja"

    def test_no_hay_bandera_naranja_ni_negra_en_shein(self, client, auth_headers, db_session):
        """module_shein.md regla 6: Shein no tiene apartados ni familiares,
        por lo tanto nunca debe salir 'naranja' ni 'negra' aunque el saldo
        esté muy vencido."""
        cliente = _crear_shein_cliente(client, auth_headers)
        self._set_estado(
            db_session, cliente["id_shein_cliente"], saldo=100.0,
            fecha_pago_programada=date.today() - timedelta(days=365),
        )
        clientes = client.get(f"{BASE}/clientes", headers=auth_headers).json()
        actualizado = next(c for c in clientes if c["id_shein_cliente"] == cliente["id_shein_cliente"])
        assert actualizado["bandera"] in ("roja", None)
