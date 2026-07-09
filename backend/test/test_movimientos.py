"""
Tests del módulo Movimientos (Panel Principal): contado, abono, gasto,
apartado (uno y varios artículos), forma_pago, saldo_resultante, y
cancelar_movimiento() -- incluye los 2 gaps cerrados esta sesión
(reversión de inventario en 'contado', cancelación del lote completo en
'apartado') y el fix de saldo_resultante en crear_apartado() (debía
guardar el saldo TOTAL del cliente, no el saldo_pendiente del lote).

app/api/v1/endpoints/movimientos.py solo expone registrar_movimiento(),
obtener_movimientos_cliente() y cancelar_movimiento() vía HTTP. No existe
endpoint para crear_apartado() todavía -- esos casos llaman al service
directo con `db_session`; el resto pasa por /api/v1/movimientos vía
`client` + `auth_headers` (mismo patrón de conftest.py / test_clientes.py).

Prefijo asumido: /api/v1/movimientos (consistente con /api/v1/clientes y
/api/v1/auth/login ya confirmados en conftest.py). Si el prefijo real es
otro, ajustar la constante BASE.

'gasto' sin descripcion: confirmado con el usuario que es comportamiento
intencional (descripcion es Optional). El comentario en
movimiento_service.py que dice lo contrario está desactualizado -- pendiente
de corregir por su lado, no se toca aquí.
"""

import pytest
from fastapi import HTTPException

from app.models.models import (
    Apartado,
    ApartadoArticulo,
    CategoriaInventario,
    Cliente,
    EstatusApartado,
    EstatusApartadoArticulo,
    EstatusInventario,
    FormaPago,
    Inventario,
    Movimiento,
    TipoProducto,
)
from app.schemas.apartado import ApartadoArticuloCreate, ApartadoCreate
from app.services.movimiento_service import cancelar_articulo_apartado, crear_apartado

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


def _crear_apartado_simple(db_session, id_cliente, precio=300.0, monto_primer_pago=100.0, id_producto=None):
    data = ApartadoCreate(
        id_cliente=id_cliente,
        articulos=[ApartadoArticuloCreate(id_producto=id_producto, precio_producto=precio)],
        monto_primer_pago=monto_primer_pago,
        forma_pago=FormaPago.efectivo,
    )
    return crear_apartado(db_session, data)


def _movimiento_de_apartado(db_session, id_apartado):
    return (
        db_session.query(Movimiento)
        .filter(Movimiento.id_apartado == id_apartado)
        .first()
    )


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
    """Gap 1 cerrado esta sesión: cancelar_movimiento() no revertía
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
# Apartado -- creación (sin endpoint HTTP todavía: llamada directa al service)
# ──────────────────────────────────────────────────────────────────────────

class TestCrearApartado:
    def test_un_articulo_manual_sin_id_producto(self, cliente_prueba, db_session):
        apartado = _crear_apartado_simple(db_session, cliente_prueba.id_cliente, precio=450.0, monto_primer_pago=100.0)

        assert apartado.saldo_pendiente == 350.0
        assert apartado.estatus == EstatusApartado.abierto
        assert len(apartado.articulos) == 1
        assert apartado.articulos[0].precio_producto == 450.0
        assert apartado.articulos[0].id_producto is None

    def test_varios_articulos_suma_precios(self, cliente_prueba, db_session):
        p1 = _crear_producto(db_session, stock=1, precio_venta=300)
        data = ApartadoCreate(
            id_cliente=cliente_prueba.id_cliente,
            articulos=[
                ApartadoArticuloCreate(id_producto=p1.id_producto, precio_producto=None),
                ApartadoArticuloCreate(id_producto=None, precio_producto=200.0),
            ],
            monto_primer_pago=100.0,
            forma_pago=FormaPago.efectivo,
        )
        apartado = crear_apartado(db_session, data)

        assert apartado.saldo_pendiente == 400.0  # (300 + 200) - 100
        assert len(apartado.articulos) == 2

        db_session.refresh(p1)
        assert p1.estatus == EstatusInventario.apartado

    def test_producto_con_coincidencia_autollena_precio_venta(self, cliente_prueba, db_session):
        p1 = _crear_producto(db_session, stock=1, precio_venta=777)
        data = ApartadoCreate(
            id_cliente=cliente_prueba.id_cliente,
            # precio_producto manual se ignora: gana el autollenado
            articulos=[ApartadoArticuloCreate(id_producto=p1.id_producto, precio_producto=1.0)],
            monto_primer_pago=100.0,
            forma_pago=FormaPago.efectivo,
        )
        apartado = crear_apartado(db_session, data)
        assert apartado.articulos[0].precio_producto == 777.0

    def test_monto_primer_pago_menor_a_100_rechaza(self):
        with pytest.raises(ValueError):
            ApartadoCreate(
                id_cliente=1,
                articulos=[ApartadoArticuloCreate(id_producto=None, precio_producto=200.0)],
                monto_primer_pago=50.0,
                forma_pago=FormaPago.efectivo,
            )

    def test_saldo_resultante_es_saldo_total_no_delta(self, cliente_prueba, db_session):
        """Regresión del bug encontrado y corregido esta sesión."""
        _fijar_saldo(db_session, cliente_prueba.id_cliente, 500.0)

        apartado = _crear_apartado_simple(db_session, cliente_prueba.id_cliente, precio=300.0, monto_primer_pago=100.0)
        assert apartado.saldo_pendiente == 200.0  # 300 - 100

        cliente = db_session.query(Cliente).get(cliente_prueba.id_cliente)
        assert cliente.saldo == 700.0  # 500 previo + 200 del lote

        movimiento = _movimiento_de_apartado(db_session, apartado.id_apartado)
        # Antes del fix esto guardaba 200.0 (el delta) en vez de 700.0 (el total)
        assert movimiento.saldo_resultante == 700.0

    def test_cliente_ya_tiene_apartado_abierto_rechaza(self, cliente_prueba, db_session):
        _crear_apartado_simple(db_session, cliente_prueba.id_cliente)

        with pytest.raises(HTTPException) as exc:
            _crear_apartado_simple(db_session, cliente_prueba.id_cliente)
        assert exc.value.status_code == 409


# ──────────────────────────────────────────────────────────────────────────
# Apartado -- cancelar (vía cancelar_movimiento(), sí expuesto por HTTP)
# ──────────────────────────────────────────────────────────────────────────

class TestCancelarApartado:
    """Gap 2 cerrado esta sesión: cancelar_movimiento() no contemplaba que
    el último movimiento del cliente fuera 'apartado'."""

    def test_cancela_lote_completo_varios_articulos(self, client, auth_headers, cliente_prueba, db_session):
        p1 = _crear_producto(db_session, stock=1, precio_venta=300)
        p2 = _crear_producto(db_session, stock=1, precio_venta=200)
        data = ApartadoCreate(
            id_cliente=cliente_prueba.id_cliente,
            articulos=[
                ApartadoArticuloCreate(id_producto=p1.id_producto, precio_producto=None),
                ApartadoArticuloCreate(id_producto=p2.id_producto, precio_producto=None),
            ],
            monto_primer_pago=100.0,
            forma_pago=FormaPago.efectivo,
        )
        apartado = crear_apartado(db_session, data)
        movimiento = _movimiento_de_apartado(db_session, apartado.id_apartado)

        resp = client.delete(f"{BASE}/{movimiento.id_movimiento}/cancelar", headers=auth_headers)
        assert resp.status_code == 200, resp.text

        apartado_db = db_session.query(Apartado).get(apartado.id_apartado)
        assert apartado_db.estatus == EstatusApartado.cancelado

        articulos = (
            db_session.query(ApartadoArticulo)
            .filter(ApartadoArticulo.id_apartado == apartado.id_apartado)
            .all()
        )
        assert all(a.estatus_articulo == EstatusApartadoArticulo.cancelado for a in articulos)

        db_session.refresh(p1)
        db_session.refresh(p2)
        assert p1.estatus == EstatusInventario.disponible
        assert p2.estatus == EstatusInventario.disponible

    def test_revierte_saldo_del_cliente(self, client, auth_headers, cliente_prueba, db_session):
        _fijar_saldo(db_session, cliente_prueba.id_cliente, 500.0)
        apartado = _crear_apartado_simple(db_session, cliente_prueba.id_cliente, precio=300.0, monto_primer_pago=100.0)

        cliente = db_session.query(Cliente).get(cliente_prueba.id_cliente)
        assert cliente.saldo == 700.0

        movimiento = _movimiento_de_apartado(db_session, apartado.id_apartado)
        resp = client.delete(f"{BASE}/{movimiento.id_movimiento}/cancelar", headers=auth_headers)
        assert resp.status_code == 200, resp.text

        db_session.refresh(cliente)
        assert cliente.saldo == 500.0

    def test_no_permite_cancelar_si_ya_hubo_abono(self, client, auth_headers, cliente_prueba, db_session):
        apartado = _crear_apartado_simple(db_session, cliente_prueba.id_cliente, precio=300.0, monto_primer_pago=100.0)
        movimiento = _movimiento_de_apartado(db_session, apartado.id_apartado)

        client.post(
            BASE,
            json={"operacion": "abono", "id_cliente": cliente_prueba.id_cliente, "monto": 50, "forma_pago": "efectivo"},
            headers=auth_headers,
        )

        resp = client.delete(f"{BASE}/{movimiento.id_movimiento}/cancelar", headers=auth_headers)
        assert resp.status_code == 409

    def test_no_reabre_articulos_ya_cancelados_manualmente(self, client, auth_headers, cliente_prueba, db_session):
        """Si el cliente ya canceló 1 de 2 artículos vía
        cancelar_articulo_apartado() antes de deshacer todo el movimiento,
        ese artículo no debe tocarse de nuevo -- solo los que seguían
        'vigente'."""
        p1 = _crear_producto(db_session, stock=1, precio_venta=300)
        p2 = _crear_producto(db_session, stock=1, precio_venta=200)
        data = ApartadoCreate(
            id_cliente=cliente_prueba.id_cliente,
            articulos=[
                ApartadoArticuloCreate(id_producto=p1.id_producto, precio_producto=None),
                ApartadoArticuloCreate(id_producto=p2.id_producto, precio_producto=None),
            ],
            monto_primer_pago=100.0,
            forma_pago=FormaPago.efectivo,
        )
        apartado = crear_apartado(db_session, data)
        articulo_p1 = next(a for a in apartado.articulos if a.id_producto == p1.id_producto)
        cancelar_articulo_apartado(db_session, articulo_p1.id_apartado_articulo)

        movimiento = _movimiento_de_apartado(db_session, apartado.id_apartado)
        resp = client.delete(f"{BASE}/{movimiento.id_movimiento}/cancelar", headers=auth_headers)
        assert resp.status_code == 200, resp.text

        articulos = (
            db_session.query(ApartadoArticulo)
            .filter(ApartadoArticulo.id_apartado == apartado.id_apartado)
            .all()
        )
        assert all(a.estatus_articulo == EstatusApartadoArticulo.cancelado for a in articulos)


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
