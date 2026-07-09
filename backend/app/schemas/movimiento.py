from pydantic import BaseModel, field_validator, model_validator
from typing import Optional
from datetime import datetime
from app.models.models import Operacion, FormaPago


class MovimientoCreate(BaseModel):
    operacion:   Operacion
    id_cliente:  Optional[int] = None
    id_producto: Optional[int] = None
    monto:       float
    forma_pago:  FormaPago
    descripcion: Optional[str] = None

    @field_validator("monto")
    @classmethod
    def monto_positivo(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("El monto debe ser mayor a 0")
        return v

    @model_validator(mode="after")
    def validar_reglas_operacion(self) -> "MovimientoCreate":
        if self.operacion in (Operacion.apartado, Operacion.abono):
            if self.id_cliente is None:
                raise ValueError(
                    f"La operación '{self.operacion.value}' requiere un cliente"
                )
        if self.operacion == Operacion.gasto:
            if self.id_cliente is not None:
                raise ValueError("La operación 'gasto' no lleva cliente")
        return self


class MovimientoRead(BaseModel):
    id_movimiento:    int
    operacion:        Operacion
    id_cliente:       Optional[int]
    id_producto:      Optional[int]
    monto:            float
    forma_pago:       FormaPago
    saldo_resultante: Optional[float]
    descripcion:      Optional[str]
    fecha:            Optional[datetime]

    model_config = {"from_attributes": True}
