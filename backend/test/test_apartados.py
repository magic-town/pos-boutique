"""
Tests del módulo Apartado que NO están ya cubiertos en test_movimientos.py
(REGLAS_NEGOCIO.md §5, module_movimientos.md).

test_movimientos.py ya cubre, dentro de sus propias clases TestCrearApartado
y TestCancelarApartado: suma de precios de varios artículos, autollenado de
precio_venta cuando hay coincidencia en inventario, el mínimo de $100 en
monto_primer_pago, saldo_resultante = saldo total (no delta), el rechazo de
un segundo apartado abierto, y la cancelación del lote completo vía
cancelar_movimiento(). Ese archivo no se toca ni se duplica aquí.

Este archivo cubre lo que queda: validaciones de schema a nivel de artículo
individual (ApartadoArticuloCreate), la resolución de precio en
crear_apartado() cuando id_producto NO tiene coincidencia en inventario
(_DISPONIBLES), obtener_apartado_abierto() (usado por Abono para saldo_pendiente
en vivo), y el ciclo de vida completo de cancelar_articulo_apartado()
(REGLAS_NEGOCIO.md §5, regla 6: cancelar 1 artículo no toca saldo_pendiente
ni clientes.saldo, y el lote nunca se da de baja como unidad por esta vía).

No existe endpoint HTTP para crear_apartado() ni para cancelar_articulo_apartado()
todavía (mismo comentario que test_movimientos.py) -- se llama directo al
service con `db_session`.
"""

import pytest
from fastapi import HTTPException

from app.models.models import (
    ApartadoArticulo,
    CategoriaInventario,
    Cliente,
    EstatusApartado,
    EstatusApartadoArticulo,
    EstatusInventario,
    FormaPago,
    Inventario,
    TipoProducto,
)
from app.schemas.apartado import ApartadoArticuloCreate, ApartadoCreate
from app.services.movimiento_service import (
    cancelar_articulo_apartado,
    crear_apartado,
    obtener_apartado_abierto,
)


# ──────────────────────────────────────────────────────────────────────────
# Helpers locales (mismo criterio que test_movimientos.py: cada archivo de
# test define los suyos, no se importan entre archivos)
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


def _crear_apartado_simple(db_session, id_cliente, precio=300.0, monto_primer_pago=100.0, id_producto=None):
    data = ApartadoCreate(
        id_cliente=id_cliente,
        articulos=[ApartadoArticuloCreate(id_producto=id_producto, precio_producto=precio)],
        monto_primer_pago=monto_primer_pago,
        forma_pago=FormaPago.efectivo,
    )
    return crear_apartado(db_session, data)


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
# obtener_apartado_abierto() -- usado por Abono para mostrar saldo_pendiente
# en vivo al buscar cliente
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
# cancelar_articulo_apartado() -- REGLAS_NEGOCIO.md §5, regla 6
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
        completo como unidad es responsabilidad de cancelar_movimiento(),
        fuera del alcance de este archivo (ver test_movimientos.py)."""
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
