from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas.movimiento import MovimientoCreate, MovimientoRead
from app.services.movimiento_service import registrar_movimiento, cancelar_movimiento, obtener_movimientos_cliente
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/movimientos", tags=["movimientos"])


@router.post("", response_model=MovimientoRead, status_code=status.HTTP_201_CREATED)
def crear_movimiento(
    data: MovimientoCreate,
    db: Session = Depends(get_db),
    _: object = Depends(get_current_user),
):
    return registrar_movimiento(db, data)


@router.get("", response_model=list[MovimientoRead])
def historial(
    id_cliente: int = Query(..., description="ID del cliente"),
    db: Session = Depends(get_db),
    _: object = Depends(get_current_user),
):
    return obtener_movimientos_cliente(db, id_cliente)


@router.delete("/{id_movimiento}/cancelar")
def cancelar(
    id_movimiento: int,
    db: Session = Depends(get_db),
    _: object = Depends(get_current_user),
):
    return cancelar_movimiento(db, id_movimiento)
