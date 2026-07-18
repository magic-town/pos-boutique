"""
Tests del módulo Movimientos (Panel Principal): contado, abono, gasto,
forma_pago, saldo_resultante, y cancelar_movimiento() -- incluye el gap
cerrado esta sesión (reversión de inventario en 'contado').

Todo lo de Apartado (creación, cancelación de artículo individual y
cancelación del lote completo) vive en test_apartados.py -- separación
limpia por módulo (REPORT.md §4.2). Este archivo no importa ni referencia
nada de Apartado.

/api/v1/movimientos expone registrar_movimiento(), obtener_movimientos_cliente()
y cancelar_movimiento() vía HTTP -- todo pasa por `client` + `auth_headers`
(mismo patrón de conftest.py / test_clientes.py).

Prefijo asumido: /api/v1/movimientos (consistente con /api/v1/clientes y
/api/v1/auth/login ya confirmados en conftest.py). Si el prefijo real es
otro, ajustar la constante BASE.

'gasto' sin descripcion: confirmado con el usuario que es comportamiento
intencional (descripcion es Optional). El comentario en
movimiento_service.py que dice lo contrario está desactualizado -- pendiente
de corregir por su lado, no se toca aquí.
"""

from app.models.models import (
    CategoriaInventario,
    Cliente,
    EstatusInventario,
    Inventario,
    TipoProducto,
)

BASE = "/api/v1/movimientos"


# ──────────────────────────────────────────────────────────────────────────
# Helpers locales (Inventario no tiene endpoint en el alcance de este
# módulo -- se inserta directo vía db_session, mismo criterio que
# cliente_prueba usaba antes de que POST /clientes funcionara)
# ──────────────────────────────────────────────────────────────────────────

def _crear_producto(db_session, stock=3, precio_venta=500, precio_descuento=None):
    estatus = (
        EstatusInventario.disponible_c_descuento
        if precio_descuento is not None
        else EstatusInventario.disponible
    )
    producto = Inventario(
        categoria=CategoriaInventario.dama,
        tipo_producto=TipoProducto.formal,
        descripcion="Producto de prueba -- test_movimientos",
        precio_venta=precio_venta,
        precio_descuento=precio_descuento,
        stock=stock,
        estatus=estatus,
    )
    db_session.add(producto)
    db_session.commit()
    db_session.refresh(producto)
    return producto


def _fijar_saldo(db_session, id_cliente, saldo):
    cliente = db_session.query(Cliente).get(id_cliente)
    cliente.saldo = saldo
    db_session.commit()
    return cliente


# ──────────────────────────────────────────────────────────────────────────
# Contado
# ──────────────────────────────────────────────────────────────────────────

class TestContado:
    def test_con_producto_descuenta_stock_sin_agotar(self, client, auth_headers, db_session):
        producto = _crear_producto(db_session, stock=3, precio_venta=500)
        resp = client.post(
            BASE,
            json={"operacion": "contado", "id_producto": producto.id_producto, "monto": 500, "forma_pago": "efectivo"},
            headers=auth_headers,
        )
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["saldo_resultante"] is None
        assert body["id_producto"] == producto.id_producto

        db_session.refresh(producto)
        assert producto.stock == 2
        assert producto.estatus == EstatusInventario.disponible

    def test_agota_stock_pasa_a_vendido(self, client, auth_headers, db_session):
        producto = _crear_producto(db_session, stock=1, precio_venta=500)
        resp = client.post(
            BASE,
            json={"operacion": "contado", "id_producto": producto.id_producto, "monto": 500, "forma_pago": "efectivo"},
            headers=auth_headers,
        )
        assert resp.status_code == 201, resp.text

        db_session.refresh(producto)
        assert producto.stock == 0
        assert producto.estatus == EstatusInventario.vendido

    def test_sin_coincidencia_en_inventario_captura_manual(self, client, auth_headers):
        resp = client.post(
            BASE,
            json={"operacion": "contado", "id_producto": 999999, "monto": 350, "forma_pago": "efectivo"},
            headers=auth_headers,
        )
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["saldo_resultante"] is None
        assert body["id_producto"] is None  # sin match, no se persiste el id enviado

    def test_monto_no_positivo_rechaza(self, client, auth_headers):
        resp = client.post(
            BASE,
            json={"operacion": "contado", "monto": 0, "forma_pago": "efectivo"},
            headers=auth_headers,
        )
        assert resp.status_code == 422


class TestCancelarContadoRevierteInventario:
    """Gap cerrado esta sesión: cancelar_movimiento() no revertía
    inventario cuando se cancelaba un movimiento 'contado'."""

    def test_regresa_stock(self, client, auth_headers, db_session):
        producto = _crear_producto(db_session, stock=2, precio_venta=500)
        resp = client.post(
            BASE,
            json={"operacion": "contado", "id_producto": producto.id_producto, "monto": 500, "forma_pago": "efectivo"},
            headers=auth_headers,
        )
        id_movimiento = resp.json()["id_movimiento"]

        resp = client.delete(f"{BASE}/{id_movimiento}/cancelar", headers=auth_headers)
        assert resp.status_code == 200, resp.text

        db_session.refresh(producto)
        assert producto.stock == 2

    def test_reactiva_producto_que_habia_quedado_vendido(self, client, auth_headers, db_session):
        producto = _crear_producto(db_session, stock=1, precio_venta=500)
        resp = client.post(
            BASE,
            json={"operacion": "contado", "id_producto": producto.id_producto, "monto": 500, "forma_pago": "efectivo"},
            headers=auth_headers,
        )
        id_movimiento = resp.json()["id_movimiento"]
        db_session.refresh(producto)
        assert producto.estatus == EstatusInventario.vendido  # precondición

        resp = client.delete(f"{BASE}/{id_movimiento}/cancelar", headers=auth_headers)
        assert resp.status_code == 200, resp.text

        db_session.refresh(producto)
        assert producto.stock == 1
        assert producto.estatus == EstatusInventario.disponible

    def test_reactiva_preservando_descuento(self, client, auth_headers, db_session):
        producto = _crear_producto(db_session, stock=1, precio_venta=500, precio_descuento=400)
        resp = client.post(
            BASE,
            json={"operacion": "contado", "id_producto": producto.id_producto, "monto": 400, "forma_pago": "efectivo"},
            headers=auth_headers,
        )
        id_movimiento = resp.json()["id_movimiento"]

        resp = client.delete(f"{BASE}/{id_movimiento}/cancelar", headers=auth_headers)
        assert resp.status_code == 200, resp.text

        db_session.refresh(producto)
        assert producto.estatus == EstatusInventario.disponible_c_descuento


# ──────────────────────────────────────────────────────────────────────────
# Abono
# ──────────────────────────────────────────────────────────────────────────

class TestAbono:
    def test_descuenta_saldo_y_saldo_resultante(self, client, auth_headers, cliente_prueba, db_session):
        _fijar_saldo(db_session, cliente_prueba.id_cliente, 1000.0)

        resp = client.post(
            BASE,
            json={"operacion": "abono", "id_cliente": cliente_prueba.id_cliente, "monto": 300, "forma_pago": "efectivo"},
            headers=auth_headers,
        )
        assert resp.status_code == 201, resp.text
        assert resp.json()["saldo_resultante"] == 700.0

        cliente = db_session.query(Cliente).get(cliente_prueba.id_cliente)
        assert cliente.saldo == 700.0

    def test_supera_saldo_rechaza(self, client, auth_headers, cliente_prueba, db_session):
        _fijar_saldo(db_session, cliente_prueba.id_cliente, 100.0)

        resp = client.post(
            BASE,
            json={"operacion": "abono", "id_cliente": cliente_prueba.id_cliente, "monto": 500, "forma_pago": "efectivo"},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_sin_cliente_rechaza(self, client, auth_headers):
        resp = client.post(
            BASE,
            json={"operacion": "abono", "monto": 100, "forma_pago": "efectivo"},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_cliente_inexistente_404(self, client, auth_headers):
        resp = client.post(
            BASE,
            json={"operacion": "abono", "id_cliente": 999999, "monto": 100, "forma_pago": "efectivo"},
            headers=auth_headers,
        )
        assert resp.status_code == 404


class TestCancelarAbono:
    def test_revierte_saldo_al_valor_anterior(self, client, auth_headers, cliente_prueba, db_session):
        _fijar_saldo(db_session, cliente_prueba.id_cliente, 1000.0)

        resp = client.post(
            BASE,
            json={"operacion": "abono", "id_cliente": cliente_prueba.id_cliente, "monto": 300, "forma_pago": "efectivo"},
            headers=auth_headers,
        )
        id_movimiento = resp.json()["id_movimiento"]

        resp = client.delete(f"{BASE}/{id_movimiento}/cancelar", headers=auth_headers)
        assert resp.status_code == 200, resp.text

        cliente = db_session.query(Cliente).get(cliente_prueba.id_cliente)
        assert cliente.saldo == 1000.0

    def test_solo_se_puede_cancelar_el_ultimo_movimiento(self, client, auth_headers, cliente_prueba, db_session):
        _fijar_saldo(db_session, cliente_prueba.id_cliente, 1000.0)

        resp1 = client.post(
            BASE,
            json={"operacion": "abono", "id_cliente": cliente_prueba.id_cliente, "monto": 100, "forma_pago": "efectivo"},
            headers=auth_headers,
        )
        id_movimiento_1 = resp1.json()["id_movimiento"]

        client.post(
            BASE,
            json={"operacion": "abono", "id_cliente": cliente_prueba.id_cliente, "monto": 100, "forma_pago": "efectivo"},
            headers=auth_headers,
        )

        resp = client.delete(f"{BASE}/{id_movimiento_1}/cancelar", headers=auth_headers)
        assert resp.status_code == 409


# ──────────────────────────────────────────────────────────────────────────
# Gasto
# ──────────────────────────────────────────────────────────────────────────

class TestGasto:
    def test_sin_cliente_ni_producto(self, client, auth_headers):
        resp = client.post(
            BASE,
            json={"operacion": "gasto", "monto": 250, "forma_pago": "efectivo", "descripcion": "Compra de bolsas"},
            headers=auth_headers,
        )
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["id_cliente"] is None
        assert body["saldo_resultante"] is None

    def test_con_cliente_rechaza(self, client, auth_headers, cliente_prueba):
        resp = client.post(
            BASE,
            json={
                "operacion": "gasto",
                "id_cliente": cliente_prueba.id_cliente,
                "monto": 100,
                "forma_pago": "efectivo",
                "descripcion": "x",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_sin_descripcion_permite(self, client, auth_headers):
        resp = client.post(
            BASE,
            json={"operacion": "gasto", "monto": 80, "forma_pago": "efectivo"},
            headers=auth_headers,
        )
        assert resp.status_code == 201, resp.text
        assert resp.json()["descripcion"] is None


# ──────────────────────────────────────────────────────────────────────────
# Historial / cancelar -- casos generales
# ──────────────────────────────────────────────────────────────────────────

class TestHistorialYCancelarGeneral:
    def test_get_historial_por_cliente(self, client, auth_headers, cliente_prueba, db_session):
        _fijar_saldo(db_session, cliente_prueba.id_cliente, 200.0)
        client.post(
            BASE,
            json={"operacion": "abono", "id_cliente": cliente_prueba.id_cliente, "monto": 50, "forma_pago": "efectivo"},
            headers=auth_headers,
        )

        resp = client.get(BASE, params={"id_cliente": cliente_prueba.id_cliente}, headers=auth_headers)
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert len(body) >= 1
        assert all(m["id_cliente"] == cliente_prueba.id_cliente for m in body)

    def test_cancelar_movimiento_inexistente_404(self, client, auth_headers):
        resp = client.delete(f"{BASE}/999999/cancelar", headers=auth_headers)
        assert resp.status_code == 404
