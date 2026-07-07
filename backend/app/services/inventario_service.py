"""
Lógica de negocio del módulo Inventario (FULLSTACK/module_inventario.md).
"""

from datetime import date

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.models import EstatusInventario, Inventario
from app.schemas.inventario import (
    CambiarEstatusRequest,
    InventarioFiltro,
    ProductoCreate,
    SegmentoDescuento,
    TRANSICIONES_VALIDAS,
)


# ──────────────────────────────────────────────────────────────────────────
# Opción 1 — Agregar Producto
# ──────────────────────────────────────────────────────────────────────────

def crear_producto(db: Session, payload: ProductoCreate) -> Inventario:
    producto = Inventario(
        categoria=payload.categoria,
        tipo_producto=payload.tipo_producto,
        descripcion=payload.descripcion,
        talla=payload.talla,
        color=payload.color,
        marca=payload.marca,
        precio_venta=payload.precio_venta,
        stock=payload.stock,
        estatus=EstatusInventario.disponible,
        precio_descuento=None,
        descripcion_ruta=None,
    )
    db.add(producto)
    db.commit()
    db.refresh(producto)
    return producto


# ──────────────────────────────────────────────────────────────────────────
# Opción 2 — Cambiar Estatus
# ──────────────────────────────────────────────────────────────────────────

def cambiar_estatus(db: Session, id_producto: int, payload: CambiarEstatusRequest) -> Inventario:
    producto = db.query(Inventario).filter(Inventario.id_producto == id_producto).first()
    if producto is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Producto no encontrado.")

    if payload.nuevo_estatus not in TRANSICIONES_VALIDAS.get(producto.estatus, set()):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Transición inválida: '{producto.estatus.value}' -> '{payload.nuevo_estatus.value}'.",
        )

    if payload.nuevo_estatus == EstatusInventario.disponible_c_descuento:
        if payload.precio_descuento >= producto.precio_venta:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "precio_descuento debe ser menor que precio_venta.",
            )

    try:
        producto.estatus = payload.nuevo_estatus
        producto.descripcion_ruta = (
            payload.descripcion_ruta if payload.nuevo_estatus == EstatusInventario.en_ruta else None
        )
        # module_inventario.md, tabla de estatus: 'disponible' siempre limpia
        # el descuento; 'disponible_c/descuento' lo fija al valor capturado;
        # 'en_ruta'/'apartado'/'vendido' lo CONSERVAN tal cual estaba
        # ("NULL o valor" en la tabla) -- no se tocan.
        if payload.nuevo_estatus == EstatusInventario.disponible:
            producto.precio_descuento = None
        elif payload.nuevo_estatus == EstatusInventario.disponible_c_descuento:
            producto.precio_descuento = payload.precio_descuento
        # REGLAS_NEGOCIO.md §4.3 / invariante §11: todo cambio de `estatus`
        # debe actualizar `changed_status` en la misma transacción.
        producto.changed_status = date.today()
        db.commit()
        db.refresh(producto)
        return producto
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise


# ──────────────────────────────────────────────────────────────────────────
# Opción 3 — Consulta Inventario
# ──────────────────────────────────────────────────────────────────────────

def consultar_inventario(db: Session, filtro: InventarioFiltro) -> list[Inventario]:
    query = db.query(Inventario)
    if filtro.categoria is not None:
        query = query.filter(Inventario.categoria == filtro.categoria)
    if filtro.tipo_producto is not None:
        query = query.filter(Inventario.tipo_producto == filtro.tipo_producto)
    if filtro.estatus is not None:
        query = query.filter(Inventario.estatus == filtro.estatus)
    if filtro.marca is not None:
        query = query.filter(Inventario.marca == filtro.marca)
    return query.order_by(Inventario.id_producto.asc()).all()


# ──────────────────────────────────────────────────────────────────────────
# Opción 4 / 5 — Descuento Masivo
# ──────────────────────────────────────────────────────────────────────────

def _aplicar_filtro_segmento(query, segmento: SegmentoDescuento):
    if segmento.categoria is not None:
        query = query.filter(Inventario.categoria == segmento.categoria)
    if segmento.tipo_producto is not None:
        query = query.filter(Inventario.tipo_producto == segmento.tipo_producto)
    if segmento.marca is not None:
        query = query.filter(Inventario.marca == segmento.marca)
    if segmento.talla is not None:
        query = query.filter(Inventario.talla == segmento.talla)
    if segmento.color is not None:
        query = query.filter(Inventario.color == segmento.color)
    if segmento.ids_producto is not None:
        query = query.filter(Inventario.id_producto.in_(segmento.ids_producto))
    return query


def aplicar_descuento_masivo(
    db: Session, segmento: SegmentoDescuento, pct: float | None, precio_fijo: int | None,
) -> tuple[int, list[int]]:
    """Solo toca productos en estatus 'disponible' (module_inventario.md
    Opción 4). Devuelve (productos_afectados, ids_omitidos_por_precio_invalido)."""
    query = _aplicar_filtro_segmento(db.query(Inventario), segmento)
    query = query.filter(Inventario.estatus == EstatusInventario.disponible)
    productos = query.all()

    afectados = 0
    omitidos: list[int] = []
    try:
        for producto in productos:
            nuevo_precio = (
                round(producto.precio_venta * (1 - pct / 100))
                if pct is not None else precio_fijo
            )
            if nuevo_precio >= producto.precio_venta:
                omitidos.append(producto.id_producto)
                continue
            producto.precio_descuento = nuevo_precio
            producto.estatus = EstatusInventario.disponible_c_descuento
            producto.changed_status = date.today()
            afectados += 1
        db.commit()
        return afectados, omitidos
    except Exception:
        db.rollback()
        raise


def retirar_descuento_masivo(db: Session, segmento: SegmentoDescuento) -> int:
    """Solo revierte productos actualmente 'disponible_c/descuento'
    (module_inventario.md Opción 5) -- no toca vendido/apartado con
    descuento histórico."""
    query = _aplicar_filtro_segmento(db.query(Inventario), segmento)
    query = query.filter(Inventario.estatus == EstatusInventario.disponible_c_descuento)
    productos = query.all()

    try:
        for producto in productos:
            producto.precio_descuento = None
            producto.estatus = EstatusInventario.disponible
            producto.changed_status = date.today()
        db.commit()
        return len(productos)
    except Exception:
        db.rollback()
        raise
