from pydantic import BaseModel, field_validator, model_validator
from typing import Optional
from datetime import datetime


class PedidoCreate(BaseModel):
    id_cliente:          int
    producto:            str
    id_producto_externo: Optional[str] = None
    marca:               Optional[str] = None
    talla:               Optional[str] = None
    opcion_producto:     Optional[str] = None
    opcion_marca:        Optional[str] = None
    opcion_talla:        Optional[str] = None

    @field_validator("producto")
    @classmethod
    def producto_no_vacio(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("El producto no puede estar vacío")
        return v.strip()

    @model_validator(mode="after")
    def validar_opcion(self) -> "PedidoCreate":
        opcion_campos = [self.opcion_producto, self.opcion_marca, self.opcion_talla]
        tiene_alguno = any(c is not None for c in opcion_campos)
        if tiene_alguno and not self.opcion_producto:
            raise ValueError(
                "Si se registra una opción alternativa, 'opcion_producto' es obligatorio"
            )
        return self


class PedidoRead(BaseModel):
    id_pedido:           int
    id_cliente:          int
    producto:            str
    id_producto_externo: Optional[str]
    marca:               Optional[str]
    talla:               Optional[str]
    opcion_producto:     Optional[str]
    opcion_marca:        Optional[str]
    opcion_talla:        Optional[str]
    fecha:               Optional[datetime]

    model_config = {"from_attributes": True}
