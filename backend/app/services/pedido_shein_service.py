from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException, status
from app.models.models import (
    SheinCliente,
    SheinPedido,
    SheinPedidoArticulo,
    SheinCorte,
    EstatusArticuloShein,
    EstatusPago,
)
from app.schemas.pedido_shein import (
    SheinClienteCreate,
    SheinPedidoCreate,
    SheinArticuloEstatusUpdate,
    SheinCorteCreate,
    SheinPedidoRead,
    SheinArticuloRead,
)


# ──────────────────────────────────────────────────────────────────────────
# SHEIN CLIENTE
# ──────────────────────────────────────────────────────────────────────────

def crear_shein_cliente(db: Session, data: SheinClienteCreate) -> SheinCliente:
    cliente = SheinCliente(
        nombre=data.nombre,
        colonia=data.colonia,
        telefono=data.telefono,
    )
    db.add(cliente)
    db.commit()
    db.refresh(cliente)
    return cliente


def obtener_shein_clientes(db: Session) -> list[SheinCliente]:
    return db.query(SheinCliente).order_by(SheinCliente.nombre).all()


# ──────────────────────────────────────────────────────────────────────────
# SHEIN PEDIDO
# ──────────────────────────────────────────────────────────────────────────

def _monto_efectivo(articulo: SheinPedidoArticulo) -> float:
    return articulo.monto_vigente if articulo.monto_vigente is not None else articulo.monto


def _monto_pedido(pedido: SheinPedido) -> float:
    """REGLAS_NEGOCIO §6 regla 8: monto_pedido se deriva siempre filtrando
    estatus_articulo = 'confirmado' — nunca se replica como cálculo aparte."""
    return sum(
        _monto_efectivo(a)
        for a in pedido.articulos
        if a.estatus_articulo == EstatusArticuloShein.confirmado
    )


def _pedido_a_read(pedido: SheinPedido) -> SheinPedidoRead:
    return SheinPedidoRead(
        id_shein_pedido=pedido.id_shein_pedido,
        id_shein_cliente=pedido.id_shein_cliente,
        id_shein_corte=pedido.id_shein_corte,
        estatus_pago=pedido.estatus_pago,
        fecha=pedido.fecha,
        articulos=[SheinArticuloRead.model_validate(a) for a in pedido.articulos],
        monto_pedido=_monto_pedido(pedido),
    )


def crear_shein_pedido(db: Session, data: SheinPedidoCreate) -> SheinPedidoRead:
    cliente = db.query(SheinCliente).filter(
        SheinCliente.id_shein_cliente == data.id_shein_cliente
    ).first()
    if not cliente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cliente Shein {data.id_shein_cliente} no encontrado",
        )

    pedido = SheinPedido(id_shein_cliente=data.id_shein_cliente)
    pedido.articulos = [
        SheinPedidoArticulo(
            id_articulo=a.id_articulo,
            producto=a.producto,
            tipo_producto=a.tipo_producto,
            monto=a.monto,
        )
        for a in data.articulos
    ]
    db.add(pedido)
    db.commit()
    db.refresh(pedido)
    return _pedido_a_read(pedido)


def obtener_shein_pedidos(
    db: Session,
    id_shein_cliente: int | None = None,
    sin_corte: bool = False,
) -> list[SheinPedidoRead]:
    query = db.query(SheinPedido).options(joinedload(SheinPedido.articulos))
    if id_shein_cliente is not None:
        query = query.filter(SheinPedido.id_shein_cliente == id_shein_cliente)
    if sin_corte:
        query = query.filter(SheinPedido.id_shein_corte.is_(None))
    pedidos = query.order_by(SheinPedido.fecha.desc()).all()
    return [_pedido_a_read(p) for p in pedidos]


def actualizar_estatus_articulo(
    db: Session, id_shein_articulo: int, data: SheinArticuloEstatusUpdate
) -> SheinPedidoArticulo:
    """Resuelve un artículo (confirmado/cancelado) antes del corte. Necesario porque
    REGLAS_NEGOCIO exige confirmación explícita del cliente ante variación de precio,
    y monto_pedido/suma_pedidos solo cuentan artículos 'confirmado'."""
    articulo = db.query(SheinPedidoArticulo).filter(
        SheinPedidoArticulo.id_shein_articulo == id_shein_articulo
    ).first()
    if not articulo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Artículo Shein {id_shein_articulo} no encontrado",
        )
    if articulo.pedido.id_shein_corte is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El pedido ya fue incluido en un corte; no se puede modificar el artículo",
        )

    articulo.estatus_articulo = data.estatus_articulo
    if data.monto_vigente is not None:
        articulo.monto_vigente = data.monto_vigente
    db.commit()
    db.refresh(articulo)
    return articulo


# ──────────────────────────────────────────────────────────────────────────
# SHEIN CORTE
# ──────────────────────────────────────────────────────────────────────────

def crear_shein_corte(db: Session, data: SheinCorteCreate) -> SheinCorte:
    pedidos = (
        db.query(SheinPedido)
        .options(joinedload(SheinPedido.articulos))
        .filter(SheinPedido.id_shein_pedido.in_(data.id_shein_pedidos))
        .all()
    )

    encontrados = {p.id_shein_pedido for p in pedidos}
    faltantes = set(data.id_shein_pedidos) - encontrados
    if faltantes:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pedidos Shein no encontrados: {sorted(faltantes)}",
        )

    ya_en_corte = [p.id_shein_pedido for p in pedidos if p.id_shein_corte is not None]
    if ya_en_corte:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Pedidos ya incluidos en un corte previo: {sorted(ya_en_corte)}",
        )

    sin_resolver = [
        p.id_shein_pedido
        for p in pedidos
        if any(a.estatus_articulo == EstatusArticuloShein.vigente for a in p.articulos)
    ]
    if sin_resolver:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Los siguientes pedidos tienen artículos sin confirmar o cancelar "
                f"contra el proveedor: {sorted(sin_resolver)}"
            ),
        )

    # Un pedido cuyos artículos quedaron todos 'cancelado' se considera cancelado
    # por completo: no recibe id_shein_corte ni estatus_pago (REPORT §3).
    pedidos_incluidos = [p for p in pedidos if _monto_pedido(p) > 0]

    total_pedidos = len(pedidos_incluidos)
    suma_pedidos = sum(_monto_pedido(p) for p in pedidos_incluidos)
    cupon = suma_pedidos - data.total_ticket

    corte = SheinCorte(
        fecha_corte=data.fecha_corte,
        total_pedidos=total_pedidos,
        suma_pedidos=suma_pedidos,
        total_ticket=data.total_ticket,
        cupon=cupon,
    )
    db.add(corte)
    db.flush()  # asigna id_shein_corte sin cerrar la transacción

    for p in pedidos_incluidos:
        p.id_shein_corte = corte.id_shein_corte
        p.estatus_pago = EstatusPago.pago_pendiente

    db.commit()
    db.refresh(corte)
    return corte


def obtener_shein_cortes(db: Session) -> list[SheinCorte]:
    return db.query(SheinCorte).order_by(SheinCorte.fecha_corte.desc()).all()


def obtener_shein_corte(db: Session, id_shein_corte: int) -> SheinCorte:
    corte = db.query(SheinCorte).filter(
        SheinCorte.id_shein_corte == id_shein_corte
    ).first()
    if not corte:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Corte Shein {id_shein_corte} no encontrado",
        )
    return corte
