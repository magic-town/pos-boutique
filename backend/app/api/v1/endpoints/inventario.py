"""
Endpoints del módulo Inventario (FULLSTACK/module_inventario.md).

Falta registrar en main.py: app.include_router(inventario.router, prefix="/api/v1")
-- a diferencia de Pedidos, este router es nuevo, no reemplaza uno existente.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.inventario import (
    AplicarDescuentoMasivoRequest,
    CambiarEstatusRequest,
    DescuentoMasivoResultado,
    InventarioFiltro,
    ProductoCreate,
    ProductoRead,
    RetirarDescuentoMasivoRequest,
)
from app.services import inventario_service
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/inventario", tags=["Inventario"])


@router.post("", response_model=ProductoRead, status_code=201)
def agregar_producto(
    payload: ProductoCreate,
    db: Session = Depends(get_db),
    _usuario=Depends(get_current_user),
):
    return inventario_service.crear_producto(db, payload)


@router.patch("/{id_producto}/estatus", response_model=ProductoRead)
def cambiar_estatus(
    id_producto: int,
    payload: CambiarEstatusRequest,
    db: Session = Depends(get_db),
    _usuario=Depends(get_current_user),
):
    return inventario_service.cambiar_estatus(db, id_producto, payload)


@router.get("", response_model=list[ProductoRead])
def consultar_inventario(
    filtro: InventarioFiltro = Depends(),
    db: Session = Depends(get_db),
    _usuario=Depends(get_current_user),
):
    return inventario_service.consultar_inventario(db, filtro)


@router.post("/descuento-masivo", response_model=DescuentoMasivoResultado)
def aplicar_descuento_masivo(
    payload: AplicarDescuentoMasivoRequest,
    db: Session = Depends(get_db),
    _usuario=Depends(get_current_user),
):
    afectados, omitidos = inventario_service.aplicar_descuento_masivo(
        db, payload.segmento, payload.pct, payload.precio_fijo,
    )
    return DescuentoMasivoResultado(productos_afectados=afectados, productos_omitidos=omitidos)


@router.post("/descuento-masivo/retirar", response_model=DescuentoMasivoResultado)
def retirar_descuento_masivo(
    payload: RetirarDescuentoMasivoRequest,
    db: Session = Depends(get_db),
    _usuario=Depends(get_current_user),
):
    afectados = inventario_service.retirar_descuento_masivo(db, payload.segmento)
    return DescuentoMasivoResultado(productos_afectados=afectados, productos_omitidos=[])
