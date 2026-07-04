"""
Lógica de negocio del módulo Pedidos (REGLAS_NEGOCIO.md §3, module_pedidos.md).

Reemplaza por completo el service plano anterior (Pedido(producto=..., marca=...,
talla=...)) -- REPORT.md §4.1 confirma que no hay nada reutilizable de ahí.

Invariante global respetada en todo este archivo (REGLAS_NEGOCIO.md §11):
el saldo del cliente NUNCA se sobrescribe -- siempre += o -=.
"""

from datetime import date

from fastapi import HTTPException, status
from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.models.models import (
    Cliente,
    EstatusArticulo,
    Pedido,
    PedidoArticulo,
    PrecioCatalogo,
    Proveedor,
    ProveedorCatalogo,
    RolArticulo,
    TipoProducto,
)
from app.schemas.pedido import ArticuloCreate, PedidoCreate

# Proveedores que tienen catálogo digitalizado con lookup automático de precio.
# 'otro' se excluye a propósito: es captura manual (REGLAS_NEGOCIO.md §3 regla 4).
_PROVEEDORES_CON_CATALOGO = {
    Proveedor.Price_Shoes: ProveedorCatalogo.Price_Shoes,
    Proveedor.Pakar: ProveedorCatalogo.Pakar,
    Proveedor.Cklass: ProveedorCatalogo.Cklass,
}


# ──────────────────────────────────────────────────────────────────────────
# Helpers comunes
# ──────────────────────────────────────────────────────────────────────────

def resolver_cliente(db: Session, no_cliente: str) -> Cliente:
    """Resuelve no_cliente -> Cliente. Lanza 404 con el mensaje exacto de
    module_pedidos.md si no existe."""
    cliente = db.query(Cliente).filter(Cliente.no_cliente == no_cliente).first()
    if cliente is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente no encontrado. Regístralo primero en el módulo Clientes.",
        )
    return cliente


def lookup_precio(db: Session, proveedor: Proveedor, id_producto: str) -> int | None:
    """SELECT precio_venta ... ORDER BY fecha_catalogo DESC LIMIT 1
    (REGLAS_NEGOCIO.md §3 regla 4 / module_pedidos.md). None si no hay match
    o si el proveedor no tiene catálogo digitalizado (p. ej. 'otro')."""
    proveedor_catalogo = _PROVEEDORES_CON_CATALOGO.get(proveedor)
    if proveedor_catalogo is None or not id_producto:
        return None

    precio = (
        db.query(PrecioCatalogo)
        .filter(
            PrecioCatalogo.proveedor == proveedor_catalogo,
            PrecioCatalogo.id_producto == id_producto,
        )
        .order_by(PrecioCatalogo.fecha_catalogo.desc())
        .first()
    )
    return precio.precio_venta if precio else None


def _resolver_monto(db: Session, articulo: ArticuloCreate) -> float | None:
    """Aplica la regla de resolución de monto (REGLAS_NEGOCIO.md §3 regla 4):
    - formal + proveedor con catálogo: lookup, gana sobre lo enviado por el
      cliente (el campo es solo-lectura en el formulario cuando hay catálogo).
    - formal + proveedor = otro: captura manual (ya validada en el schema).
    - informal: libre, tal cual se recibió."""
    if articulo.tipo_producto == TipoProducto.informal:
        return articulo.monto

    if articulo.proveedor in _PROVEEDORES_CON_CATALOGO and articulo.id_producto:
        encontrado = lookup_precio(db, articulo.proveedor, articulo.id_producto)
        if encontrado is not None:
            return float(encontrado)
        # id_producto no existe en el catálogo: queda vacío y editable
        # (mismo comportamiento documentado), no se fuerza error.
        return articulo.monto

    return articulo.monto  # proveedor == otro, ya validado como obligatorio


def _crear_articulo(
    db: Session,
    id_pedido: int,
    articulo: ArticuloCreate,
    rol: RolArticulo,
    id_articulo_principal: int | None = None,
) -> PedidoArticulo:
    monto = _resolver_monto(db, articulo)
    obj = PedidoArticulo(
        id_pedido=id_pedido,
        rol=rol,
        id_articulo_principal=id_articulo_principal,
        tipo_producto=articulo.tipo_producto,
        proveedor=articulo.proveedor,
        id_producto=articulo.id_producto,
        producto=articulo.producto,
        marca=articulo.marca,
        talla=articulo.talla,
        monto=monto,
        estatus_articulo=EstatusArticulo.vigente,
        id_articulo_sustituye=articulo.id_articulo_sustituye,
    )
    db.add(obj)
    db.flush()  # necesitamos su id_articulo para la alternativa (FK principal)
    return obj


# ──────────────────────────────────────────────────────────────────────────
# Opción 1 — Registrar Pedido
# ──────────────────────────────────────────────────────────────────────────

def crear_pedido(db: Session, payload: PedidoCreate) -> Pedido:
    cliente = resolver_cliente(db, payload.no_cliente)

    try:
        pedido = Pedido(id_cliente=cliente.id_cliente)
        db.add(pedido)
        db.flush()  # necesitamos id_pedido para las líneas

        for slot in payload.articulos:
            principal = _crear_articulo(db, pedido.id_pedido, slot.principal, RolArticulo.principal)
            for alternativa in slot.alternativas:
                _crear_articulo(
                    db,
                    pedido.id_pedido,
                    alternativa,
                    RolArticulo.alternativa,
                    id_articulo_principal=principal.id_articulo,
                )
        # El saldo NO se modifica aquí -- se modifica al marcar en_almacen
        # (REGLAS_NEGOCIO.md §3 regla 3).
        db.commit()
        db.refresh(pedido)
        return pedido
    except Exception:
        db.rollback()
        raise


# ──────────────────────────────────────────────────────────────────────────
# Opción 2 — Registrar Devolución
# ──────────────────────────────────────────────────────────────────────────

def obtener_articulos_devolvibles(db: Session, no_cliente: str) -> list[PedidoArticulo]:
    """Artículos en_almacen del cliente -- candidatos a devolución
    (module_pedidos.md, paso_2 de ventana_registrar_devolucion)."""
    cliente = resolver_cliente(db, no_cliente)
    return (
        db.query(PedidoArticulo)
        .join(Pedido, PedidoArticulo.id_pedido == Pedido.id_pedido)
        .filter(
            Pedido.id_cliente == cliente.id_cliente,
            PedidoArticulo.estatus_articulo == EstatusArticulo.en_almacen,
            PedidoArticulo.rol == RolArticulo.principal,
        )
        .all()
    )


def registrar_devolucion(db: Session, no_cliente: str, id_articulo: int) -> PedidoArticulo:
    """Transacción única (REGLAS_NEGOCIO.md §3 regla 5, module_pedidos.md
    'Flujo de una devolución'): marca devuelto + revierte saldo."""
    cliente = resolver_cliente(db, no_cliente)

    articulo = (
        db.query(PedidoArticulo)
        .join(Pedido, PedidoArticulo.id_pedido == Pedido.id_pedido)
        .filter(
            PedidoArticulo.id_articulo == id_articulo,
            Pedido.id_cliente == cliente.id_cliente,
        )
        .first()
    )
    if articulo is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Artículo no encontrado para este cliente.")
    if articulo.estatus_articulo != EstatusArticulo.en_almacen:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Solo se pueden devolver artículos con estatus 'en_almacen'.",
        )

    try:
        articulo.estatus_articulo = EstatusArticulo.devuelto
        if articulo.monto is not None:
            cliente.saldo -= articulo.monto  # invariante: nunca se sobrescribe
        db.commit()
        db.refresh(articulo)
        return articulo
    except Exception:
        db.rollback()
        raise


# ──────────────────────────────────────────────────────────────────────────
# Opción 3 — Cancelar Artículo
# ──────────────────────────────────────────────────────────────────────────

def obtener_articulos_cancelables(db: Session, no_cliente: str) -> list[PedidoArticulo]:
    cliente = resolver_cliente(db, no_cliente)
    return (
        db.query(PedidoArticulo)
        .join(Pedido, PedidoArticulo.id_pedido == Pedido.id_pedido)
        .filter(
            Pedido.id_cliente == cliente.id_cliente,
            PedidoArticulo.estatus_articulo.in_(
                [EstatusArticulo.vigente, EstatusArticulo.en_almacen]
            ),
            PedidoArticulo.rol == RolArticulo.principal,
        )
        .all()
    )


def cancelar_articulo(db: Session, no_cliente: str, id_articulo: int) -> PedidoArticulo:
    """Transacción única (REGLAS_NEGOCIO.md §3 regla 5, module_pedidos.md
    'Flujo de una cancelación'). Solo revierte saldo si el artículo ya
    había impactado saldo (estatus previo = en_almacen)."""
    cliente = resolver_cliente(db, no_cliente)

    articulo = (
        db.query(PedidoArticulo)
        .join(Pedido, PedidoArticulo.id_pedido == Pedido.id_pedido)
        .filter(
            PedidoArticulo.id_articulo == id_articulo,
            Pedido.id_cliente == cliente.id_cliente,
        )
        .first()
    )
    if articulo is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Artículo no encontrado para este cliente.")
    if articulo.estatus_articulo not in (EstatusArticulo.vigente, EstatusArticulo.en_almacen):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Solo se pueden cancelar artículos en estatus 'vigente' o 'en_almacen'.",
        )

    try:
        estatus_previo = articulo.estatus_articulo
        articulo.estatus_articulo = EstatusArticulo.cancelado
        if estatus_previo == EstatusArticulo.en_almacen and articulo.monto is not None:
            cliente.saldo -= articulo.monto
        db.commit()
        db.refresh(articulo)
        return articulo
    except Exception:
        db.rollback()
        raise


# ──────────────────────────────────────────────────────────────────────────
# Opción 4 — Lista de Surtido
# ──────────────────────────────────────────────────────────────────────────

def obtener_lista_surtido(db: Session, fecha_inicio: date, fecha_fin: date):
    """module_pedidos.md 'Consulta base' de la Lista de Surtido."""
    return (
        db.query(
            PedidoArticulo.id_articulo,
            Cliente.no_cliente,
            Cliente.nombre,
            PedidoArticulo.rol,
            PedidoArticulo.producto,
            PedidoArticulo.marca,
            PedidoArticulo.talla,
            PedidoArticulo.proveedor,
            PedidoArticulo.id_producto,
            PedidoArticulo.monto,
            Pedido.fecha,
        )
        .join(Pedido, PedidoArticulo.id_pedido == Pedido.id_pedido)
        .join(Cliente, Pedido.id_cliente == Cliente.id_cliente)
        .filter(
            and_(Pedido.fecha >= fecha_inicio, Pedido.fecha <= fecha_fin),
            PedidoArticulo.estatus_articulo == EstatusArticulo.vigente,
        )
        .order_by(Pedido.fecha.asc(), Cliente.no_cliente.asc(), Pedido.id_pedido.asc(), PedidoArticulo.rol.desc())
        .all()
    )


def surtir_articulo(db: Session, id_articulo: int) -> PedidoArticulo:
    """module_pedidos.md 'accion_surtir': vigente -> en_almacen, saldo += monto.
    Este es el único punto donde un pedido impacta el saldo del cliente."""
    articulo = db.query(PedidoArticulo).filter(PedidoArticulo.id_articulo == id_articulo).first()
    if articulo is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Artículo no encontrado.")
    if articulo.estatus_articulo != EstatusArticulo.vigente:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Solo se pueden surtir artículos en estatus 'vigente'.",
        )

    try:
        pedido = db.query(Pedido).filter(Pedido.id_pedido == articulo.id_pedido).first()
        cliente = db.query(Cliente).filter(Cliente.id_cliente == pedido.id_cliente).first()

        articulo.estatus_articulo = EstatusArticulo.en_almacen
        if articulo.monto is not None:
            cliente.saldo += articulo.monto
        db.commit()
        db.refresh(articulo)
        return articulo
    except Exception:
        db.rollback()
        raise
