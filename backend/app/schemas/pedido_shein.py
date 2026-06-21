from pydantic import BaseModel, field_validator
from datetime import datetime
from typing import Optional


class PedidoSheinCreate(BaseModel):
    id_cliente: int
    producto:   str
    monto:      float

    @field_validator("producto")
    @classmethod
    def producto_no_vacio(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("El producto no puede estar vacío")
        return v.strip()

    @field_validator("monto")
    @classmethod
    def monto_positivo(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("El monto debe ser mayor a 0")
        return v


class PedidoSheinRead(BaseModel):
    id_pedido_shein: int
    id_cliente:      int
    producto:        str
    monto:           float
    fecha:           Optional[datetime]

    model_config = {"from_attributes": True}
