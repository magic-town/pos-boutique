from pydantic import BaseModel, field_validator
from datetime import datetime
from app.models.models import Compania


class RecargaCreate(BaseModel):
    compania: Compania
    monto:    float

    @field_validator("monto")
    @classmethod
    def monto_positivo(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("El monto debe ser mayor a 0")
        return v


class RecargaRead(BaseModel):
    id_recarga: int
    compania:   Compania
    monto:      float
    fecha:      datetime

    model_config = {"from_attributes": True}


class RecargaResumenDia(BaseModel):
    """Fila del resumen del día (pie de ventana), agrupado por compañía.
    Ver module_recargas.md — consulta de totales del día actual."""
    compania: Compania
    qty:      int
    total:    float
