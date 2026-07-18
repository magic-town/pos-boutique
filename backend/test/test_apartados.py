"""
Tests del módulo Apartado (REGLAS_NEGOCIO.md §5, module_movimientos.md).

Cobertura de este archivo:
- Validaciones de schema a nivel de artículo individual (ApartadoArticuloCreate)
  y de lote (ApartadoCreate).
- Resolución de precio en crear_apartado() cuando id_producto NO tiene
  coincidencia en inventario (_DISPONIBLES).
- Creación del lote (crear_apartado()): reglas de negocio -- suma de precios
  de varios artículos, autollenado de precio_venta cuando hay coincidencia,
  mínimo $100 en monto_primer_pago, saldo_resultante = saldo TOTAL del
  cliente (no el delta del lote), rechazo de un segundo apartado abierto.
  Cubierta a nivel service (llamada directa) y a nivel HTTP (POST /apartados,
  contrato de la API).
- obtener_apartado_abierto() -- usado por Abono para saldo_pendiente en vivo.
  Cubierta a nivel service y vía GET /apartados/abierto.
- Ciclo de vida completo de cancelar_articulo_apartado() (REGLAS_NEGOCIO.md
  §5 regla 6: cancelar 1 artículo no toca saldo_pendiente ni clientes.saldo,
  y el lote nunca se da de baja como unidad por esta vía). Cubierta a nivel
  service y vía DELETE /apartados/articulos/{id}/cancelar.
- Cancelación del LOTE completo (movimiento 'apartado' original) -- se hace
  vía DELETE /movimientos/{id}/cancelar, la única puerta que existe para
  deshacer el lote como unidad (cancelar_movimiento() en
  app/services/movimiento_service.py). El comportamiento probado es 100% de
  Apartado, por eso vive aquí y no en test_movimientos.py, aunque la URL que
  se golpea sea la de /movimientos.

Migrado desde test_movimientos.py (clases TestCrearApartado y
TestCancelarApartado) ahora que existe app/api/v1/endpoints/apartados.py --
separación limpia por módulo (REPORT.md §4.2). test_movimientos.py ya no
importa ni referencia nada de Apartado.
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
from app.services.movimiento_service import (
    cancelar_articulo_apartado,
    crear_apartado,
    obtener_apartado_abierto,
)

BASE = "/api/v1/apartados"
MOVIMIENTOS_BASE = "/api/v1/movimientos"  # cancelar_movimiento() -- única puerta para deshacer el lote


# ──────────────────────────────────────────────────────────────────────────
# Helpers locales (cada archivo de test define los suyos, no se importan
# entre archivos -- mismo criterio que test_movimientos.py)
# ──────────────────────────────────────────────────────────────────────────

def _crear_producto(db_session, stock=3, precio_venta=500, estatus=None):
    producto = Inventario(
        categoria=CategoriaInventario.dama,
        tipo_producto=TipoProducto.formal,
        descripcion="Producto de prueba -- test_apartados",
        precio_venta=precio_venta,
        stock=stock,
        estatus=estatus or EstatusInventario.disponible,
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
    """Nivel service -- llamada directa a crear_apartado()."""
    data = ApartadoCreate(
        id_cliente=id_cliente,
        articulos=[ApartadoArticuloCreate(id_producto=id_producto, precio_producto=precio)],
        monto_primer_pago=monto_primer_pago,
        forma_pago=FormaPago.efectivo,
    )
    return crear_apartado(db_session, data)


def _payload_apartado(id_cliente, articulos, monto_primer_pago=100.0, forma_pago="efectivo"):
    """Nivel HTTP -- body JSON para POST /apartados. 'articulos' es una lista
    de dicts {"id_producto": ..., "precio_producto": ...}."""
    return {
        "id_cliente": id_cliente,
        "articulos": articulos,
        "monto_primer_pago": monto_primer_pago,
        "forma_pago": forma_pago,
    }


def _movimiento_de_apartado(db_session, id_apartado):
    return (
        db_session.query(Movimiento)
        .filter(Movimiento.id_apartado == id_apartado)
        .first()
    )


# ──────────────────────────────────────────────────────────────────────────
# Validaciones de schema -- ApartadoArticuloCreate / ApartadoCreate
# ──────────────────────────────────────────────────────────────────────────

class TestValidacionesSchema:
    def test_articulo_sin_id_producto_ni_precio_rechaza(self):
        """Sin id_producto no hay lookup posible en inventario -- el precio
        manual pasa a ser obligatorio."""
        with pytest.raises(ValueError):
            ApartadoArticuloCreate(id_producto=None, precio_producto=None)

    def test_articulo_con_id_producto_sin_precio_manual_es_valido(self):
        """Con id_producto presente, precio_producto puede venir None a
        nivel de schema -- la resolución real ocurre en el service."""
        articulo = ApartadoArticuloCreate(id_producto=1, precio_producto=None)
        assert articulo.id_producto == 1
        assert articulo.precio_producto is None

    def test_lista_articulos_vacia_rechaza(self):
        """Un apartado necesita al menos 1 artículo (Field(min_length=1))."""
        with pytest.raises(ValueError):
            ApartadoCreate(
                id_cliente=1,
                articulos=[],
                monto_primer_pago=100.0,
                forma_pago=FormaPago.efectivo,
            )


# ──────────────────────────────────────────────────────────────────────────
# Resolución de precio en crear_apartado() -- con/sin coincidencia en
# inventario (module_movimientos.md regla 3, mismo criterio que
# _resolver_monto en pedido_service.py)
# ──────────────────────────────────────────────────────────────────────────

class TestResolucionPrecio:
    def test_id_producto_sin_match_sin_precio_manual_rechaza(self, cliente_prueba, db_session):
        """id_producto que no existe en inventario y sin precio_producto
        manual -- no hay forma de resolver el precio, debe rechazarse."""
        data = ApartadoCreate(
            id_cliente=cliente_prueba.id_cliente,
            articulos=[ApartadoArticuloCreate(id_producto=999999, precio_producto=None)],
            monto_primer_pago=100.0,
            forma_pago=FormaPago.efectivo,
        )
        with pytest.raises(HTTPException) as exc:
            crear_apartado(db_session, data)
        assert exc.value.status_code == 422

    def test_producto_no_disponible_usa_precio_manual_y_no_se_liga(self, cliente_prueba, db_session):
        """Un id_producto que existe pero ya está 'vendido' no cuenta como
        coincidencia (_DISPONIBLES). Si se manda precio_producto manual, se
        respeta -- y el artículo del apartado NO queda ligado a ese
        id_producto, para no terminar apartando un producto ya vendido."""
        producto = _crear_producto(db_session, stock=0, precio_venta=999, estatus=EstatusInventario.vendido)
        data = ApartadoCreate(
            id_cliente=cliente_prueba.id_cliente,
            articulos=[ApartadoArticuloCreate(id_producto=producto.id_producto, precio_producto=250.0)],
            monto_primer_pago=100.0,
            forma_pago=FormaPago.efectivo,
        )
        apartado = crear_apartado(db_session, data)

        assert apartado.articulos[0].precio_producto == 250.0
        assert apartado.articulos[0].id_producto is None

        db_session.refresh(producto)
        assert producto.estatus == EstatusInventario.vendido  # no se tocó


# ──────────────────────────────────────────────────────────────────────────
# Creación del lote -- reglas de negocio (nivel service)
# Migrado desde test_movimientos.py::TestCrearApartado
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
        """Regresión: crear_apartado() debe guardar en el movimiento el
        saldo TOTAL del cliente, no el saldo_pendiente del lote."""
        _fijar_saldo(db_session, cliente_prueba.id_cliente, 500.0)

        apartado = _crear_apartado_simple(db_session, cliente_prueba.id_cliente, precio=300.0, monto_primer_pago=100.0)
        assert apartado.saldo_pendiente == 200.0  # 300 - 100

        cliente = db_session.query(Cliente).get(cliente_prueba.id_cliente)
        assert cliente.saldo == 700.0  # 500 previo + 200 del lote

        movimiento = _movimiento_de_apartado(db_session, apartado.id_apartado)
        assert movimiento.saldo_resultante == 700.0

    def test_cliente_ya_tiene_apartado_abierto_rechaza(self, cliente_prueba, db_session):
        _crear_apartado_simple(db_session, cliente_prueba.id_cliente)

        with pytest.raises(HTTPException) as exc:
            _crear_apartado_simple(db_session, cliente_prueba.id_cliente)
        assert exc.value.status_code == 409


# ──────────────────────────────────────────────────────────────────────────
# Creación del lote -- contrato HTTP (POST /apartados)
# ──────────────────────────────────────────────────────────────────────────

class TestCrearApartadoHTTP:
    def test_crea_y_devuelve_201(self, client, auth_headers, cliente_prueba):
        resp = client.post(
            BASE,
            json=_payload_apartado(
                cliente_prueba.id_cliente,
                [{"id_producto": None, "precio_producto": 450.0}],
                monto_primer_pago=100.0,
            ),
            headers=auth_headers,
        )
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["id_cliente"] == cliente_prueba.id_cliente
        assert body["saldo_pendiente"] == 350.0
        assert body["estatus"] == "abierto"
        assert len(body["articulos"]) == 1
        assert body["articulos"][0]["precio_producto"] == 450.0

    def test_varios_articulos_suma_precios(self, client, auth_headers, cliente_prueba, db_session):
        p1 = _crear_producto(db_session, stock=1, precio_venta=300)
        resp = client.post(
            BASE,
            json=_payload_apartado(
                cliente_prueba.id_cliente,
                [
                    {"id_producto": p1.id_producto, "precio_producto": None},
                    {"id_producto": None, "precio_producto": 200.0},
                ],
                monto_primer_pago=100.0,
            ),
            headers=auth_headers,
        )
        assert resp.status_code == 201, resp.text
        assert resp.json()["saldo_pendiente"] == 400.0  # (300 + 200) - 100

    def test_monto_primer_pago_menor_a_100_rechaza_422(self, client, auth_headers, cliente_prueba):
        resp = client.post(
            BASE,
            json=_payload_apartado(
                cliente_prueba.id_cliente,
                [{"id_producto": None, "precio_producto": 200.0}],
                monto_primer_pago=50.0,
            ),
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_cliente_ya_tiene_apartado_abierto_rechaza_409(self, client, auth_headers, cliente_prueba):
        payload = _payload_apartado(
            cliente_prueba.id_cliente,
            [{"id_producto": None, "precio_producto": 200.0}],
            monto_primer_pago=100.0,
        )
        resp1 = client.post(BASE, json=payload, headers=auth_headers)
        assert resp1.status_code == 201, resp1.text

        resp2 = client.post(BASE, json=payload, headers=auth_headers)
        assert resp2.status_code == 409

    def test_cliente_inexistente_404(self, client, auth_headers):
        resp = client.post(
            BASE,
            json=_payload_apartado(
                999999,
                [{"id_producto": None, "precio_producto": 200.0}],
                monto_primer_pago=100.0,
            ),
            headers=auth_headers,
        )
        assert resp.status_code == 404


# ──────────────────────────────────────────────────────────────────────────
# obtener_apartado_abierto() -- usado por Abono para mostrar saldo_pendiente
# en vivo al buscar cliente (nivel service)
# ──────────────────────────────────────────────────────────────────────────

class TestObtenerApartadoAbierto:
    def test_devuelve_el_apartado_abierto_del_cliente(self, cliente_prueba, db_session):
        apartado = _crear_apartado_simple(db_session, cliente_prueba.id_cliente)
        encontrado = obtener_apartado_abierto(db_session, cliente_prueba.id_cliente)
        assert encontrado is not None
        assert encontrado.id_apartado == apartado.id_apartado

    def test_none_si_no_tiene_apartado_abierto(self, cliente_prueba, db_session):
        assert obtener_apartado_abierto(db_session, cliente_prueba.id_cliente) is None


# ──────────────────────────────────────────────────────────────────────────
# obtener_apartado_abierto() -- contrato HTTP (GET /apartados/abierto)
# ──────────────────────────────────────────────────────────────────────────

class TestApartadoAbiertoHTTP:
    def test_devuelve_200_con_saldo_pendiente(self, client, auth_headers, cliente_prueba, db_session):
        apartado = _crear_apartado_simple(db_session, cliente_prueba.id_cliente, precio=300.0, monto_primer_pago=100.0)

        resp = client.get(f"{BASE}/abierto", params={"id_cliente": cliente_prueba.id_cliente}, headers=auth_headers)
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["id_apartado"] == apartado.id_apartado
        assert body["saldo_pendiente"] == 200.0

    def test_404_si_no_tiene_apartado_abierto(self, client, auth_headers, cliente_prueba):
        resp = client.get(f"{BASE}/abierto", params={"id_cliente": cliente_prueba.id_cliente}, headers=auth_headers)
        assert resp.status_code == 404


# ──────────────────────────────────────────────────────────────────────────
# cancelar_articulo_apartado() -- REGLAS_NEGOCIO.md §5, regla 6 (nivel service)
# ──────────────────────────────────────────────────────────────────────────

class TestCancelarArticuloApartado:
    def test_no_ajusta_saldo_pendiente_ni_saldo_cliente(self, cliente_prueba, db_session):
        """Regla 6: la deuda permanece -- cancelar 1 artículo del lote no
        reduce lo que el cliente debe ni lo que ya se le cargó."""
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
        saldo_pendiente_antes = apartado.saldo_pendiente

        cliente = db_session.query(Cliente).get(cliente_prueba.id_cliente)
        saldo_cliente_antes = cliente.saldo

        articulo_p1 = next(a for a in apartado.articulos if a.id_producto == p1.id_producto)
        cancelar_articulo_apartado(db_session, articulo_p1.id_apartado_articulo)

        db_session.refresh(apartado)
        db_session.refresh(cliente)
        assert apartado.saldo_pendiente == saldo_pendiente_antes
        assert cliente.saldo == saldo_cliente_antes
        assert apartado.estatus == EstatusApartado.abierto

    def test_regresa_producto_a_disponible(self, cliente_prueba, db_session):
        p1 = _crear_producto(db_session, stock=1, precio_venta=300)
        apartado = _crear_apartado_simple(
            db_session, cliente_prueba.id_cliente, id_producto=p1.id_producto, precio=None
        )
        articulo = apartado.articulos[0]

        cancelar_articulo_apartado(db_session, articulo.id_apartado_articulo)

        db_session.refresh(p1)
        assert p1.estatus == EstatusInventario.disponible

    def test_rechaza_cancelar_articulo_ya_cancelado(self, cliente_prueba, db_session):
        """Solo se pueden cancelar artículos en estatus 'vigente' -- no se
        puede cancelar dos veces el mismo."""
        p1 = _crear_producto(db_session, stock=1, precio_venta=300)
        apartado = _crear_apartado_simple(
            db_session, cliente_prueba.id_cliente, id_producto=p1.id_producto, precio=None
        )
        articulo = apartado.articulos[0]
        cancelar_articulo_apartado(db_session, articulo.id_apartado_articulo)

        with pytest.raises(HTTPException) as exc:
            cancelar_articulo_apartado(db_session, articulo.id_apartado_articulo)
        assert exc.value.status_code == 400

    def test_404_si_articulo_no_existe(self, db_session):
        with pytest.raises(HTTPException) as exc:
            cancelar_articulo_apartado(db_session, 999999)
        assert exc.value.status_code == 404

    def test_lote_sigue_abierto_aunque_se_cancelen_todos_los_articulos_uno_por_uno(
        self, cliente_prueba, db_session
    ):
        """El lote (apartados) nunca se da de baja como unidad por esta vía
        -- sigue 'abierto' hasta que saldo_pendiente llegue a 0 vía abonos,
        sin importar cuántos artículos se hayan cancelado. Cancelar el lote
        completo como unidad es responsabilidad de cancelar_movimiento()
        (ver TestCancelarApartado más abajo)."""
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

        for articulo in list(apartado.articulos):
            cancelar_articulo_apartado(db_session, articulo.id_apartado_articulo)

        db_session.refresh(apartado)
        assert apartado.estatus == EstatusApartado.abierto

        articulos = (
            db_session.query(ApartadoArticulo)
            .filter(ApartadoArticulo.id_apartado == apartado.id_apartado)
            .all()
        )
        assert all(a.estatus_articulo == EstatusApartadoArticulo.cancelado for a in articulos)


# ──────────────────────────────────────────────────────────────────────────
# cancelar_articulo_apartado() -- contrato HTTP
# (DELETE /apartados/articulos/{id_apartado_articulo}/cancelar)
# ──────────────────────────────────────────────────────────────────────────

class TestCancelarArticuloApartadoHTTP:
    def test_cancela_y_regresa_producto_a_disponible(self, client, auth_headers, cliente_prueba, db_session):
        p1 = _crear_producto(db_session, stock=1, precio_venta=300)
        apartado = _crear_apartado_simple(
            db_session, cliente_prueba.id_cliente, id_producto=p1.id_producto, precio=None
        )
        articulo = apartado.articulos[0]

        resp = client.delete(
            f"{BASE}/articulos/{articulo.id_apartado_articulo}/cancelar", headers=auth_headers
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["estatus_articulo"] == "cancelado"

        db_session.refresh(p1)
        assert p1.estatus == EstatusInventario.disponible

    def test_rechaza_cancelar_articulo_ya_cancelado_400(self, client, auth_headers, cliente_prueba, db_session):
        p1 = _crear_producto(db_session, stock=1, precio_venta=300)
        apartado = _crear_apartado_simple(
            db_session, cliente_prueba.id_cliente, id_producto=p1.id_producto, precio=None
        )
        articulo = apartado.articulos[0]
        client.delete(f"{BASE}/articulos/{articulo.id_apartado_articulo}/cancelar", headers=auth_headers)

        resp = client.delete(
            f"{BASE}/articulos/{articulo.id_apartado_articulo}/cancelar", headers=auth_headers
        )
        assert resp.status_code == 400

    def test_articulo_inexistente_404(self, client, auth_headers):
        resp = client.delete(f"{BASE}/articulos/999999/cancelar", headers=auth_headers)
        assert resp.status_code == 404


# ──────────────────────────────────────────────────────────────────────────
# Cancelación del LOTE completo -- vía DELETE /movimientos/{id}/cancelar
# (cancelar_movimiento() maneja 'apartado' como caso especial: no existe, ni
# tiene por qué existir, una puerta de cancelación de lote dentro de
# /apartados -- el lote se deshace deshaciendo el movimiento de caja que lo
# originó, mismo criterio que abono/contado)
# Migrado desde test_movimientos.py::TestCancelarApartado
# ──────────────────────────────────────────────────────────────────────────

class TestCancelarApartado:
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

        resp = client.delete(f"{MOVIMIENTOS_BASE}/{movimiento.id_movimiento}/cancelar", headers=auth_headers)
        assert resp.status_code == 200, resp.text

        db_session.refresh(apartado)
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
        resp = client.delete(f"{MOVIMIENTOS_BASE}/{movimiento.id_movimiento}/cancelar", headers=auth_headers)
        assert resp.status_code == 200, resp.text

        db_session.refresh(cliente)
        assert cliente.saldo == 500.0

    def test_no_permite_cancelar_si_ya_hubo_abono(self, client, auth_headers, cliente_prueba, db_session):
        apartado = _crear_apartado_simple(db_session, cliente_prueba.id_cliente, precio=300.0, monto_primer_pago=100.0)
        movimiento = _movimiento_de_apartado(db_session, apartado.id_apartado)

        client.post(
            MOVIMIENTOS_BASE,
            json={"operacion": "abono", "id_cliente": cliente_prueba.id_cliente, "monto": 50, "forma_pago": "efectivo"},
            headers=auth_headers,
        )

        resp = client.delete(f"{MOVIMIENTOS_BASE}/{movimiento.id_movimiento}/cancelar", headers=auth_headers)
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
        resp = client.delete(f"{MOVIMIENTOS_BASE}/{movimiento.id_movimiento}/cancelar", headers=auth_headers)
        assert resp.status_code == 200, resp.text

        articulos = (
            db_session.query(ApartadoArticulo)
            .filter(ApartadoArticulo.id_apartado == apartado.id_apartado)
            .all()
        )
        assert all(a.estatus_articulo == EstatusApartadoArticulo.cancelado for a in articulos)
