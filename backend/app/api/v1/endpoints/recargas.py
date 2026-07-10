from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas.recarga import RecargaCreate, RecargaRead, RecargaResumenDia
from app.services.recarga_service import crear_recarga, obtener_totales_dia
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/recargas", tags=["recargas"])


@router.post("", response_model=RecargaRead, status_code=status.HTTP_201_CREATED)
def crear(
    data: RecargaCreate,
    db: Session = Depends(get_db),
    _: object = Depends(get_current_user),
):
    return crear_recarga(db, data)


@router.get("/resumen-dia", response_model=list[RecargaResumenDia])
def resumen_dia(
    db: Session = Depends(get_db),
    _: object = Depends(get_current_user),
):
    return obtener_totales_dia(db)
