from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.apartado import (
    ApartadoAbiertoOut,
    ApartadoArticuloRead,
    ApartadoCreate,
    ApartadoRead,
)
from app.services.movimiento_service import (
    cancelar_articulo_apartado,
    crear_apartado,
    obtener_apartado_abierto,
)
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/apartados", tags=["apartados"])


@router.post("", response_model=ApartadoRead, status_code=status.HTTP_201_CREATED)
def crear(
    data: ApartadoCreate,
    db: Session = Depends(get_db),
    _: object = Depends(get_current_user),
):
    return crear_apartado(db, data)


@router.get("/abierto", response_model=ApartadoAbiertoOut)
def apartado_abierto(
    id_cliente: int = Query(..., description="ID del cliente"),
    db: Session = Depends(get_db),
    _: object = Depends(get_current_user),
):
    """module_movimientos.md, 'Abonar / Liquidar' paso 1: muestra
    saldo_pendiente en vivo al buscar cliente. 404 si no tiene apartado
    abierto -- no es un error de negocio, es el estado normal de la
    mayoría de los clientes."""
    apartado = obtener_apartado_abierto(db, id_cliente)
    if apartado is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            f"El cliente {id_cliente} no tiene un apartado abierto",
        )
    return apartado


@router.delete("/articulos/{id_apartado_articulo}/cancelar", response_model=ApartadoArticuloRead)
def cancelar_articulo(
    id_apartado_articulo: int,
    db: Session = Depends(get_db),
    _: object = Depends(get_current_user),
):
    return cancelar_articulo_apartado(db, id_apartado_articulo)
