from pydantic import BaseModel, Field, field_validator
from datetime import date
from typing import Optional
from app.models.models import TipoProductoShein, EstatusArticuloShein, EstatusPago


# ──────────────────────────────────────────────────────────────────────────
# SHEIN CLIENTE
# ──────────────────────────────────────────────────────────────────────────

class SheinClienteCreate(BaseModel):
    nombre:   str = Field(max_length=20)
    colonia:  str = Field(max_length=12)
    telefono: int

    @field_validator("nombre", "colonia")
    @classmethod
    def campo_no_vacio(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("El campo no puede estar vacío")
        return v.strip()

    @field_validator("telefono")
    @classmethod
    def telefono_10_digitos(cls, v: int) -> int:
        if not (1000000000 <= v <= 9999999999):
            raise ValueError("El teléfono debe tener 10 dígitos")
        return v


class SheinClienteRead(BaseModel):
    id_shein_cliente: int
    nombre:           str
    colonia:          str
    telefono:         int

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────────────────────────────────────
# SHEIN PEDIDO (cabecera-detalle, 1 a 4 artículos, sin concepto de alternativa)
# ──────────────────────────────────────────────────────────────────────────

class SheinArticuloCreate(BaseModel):
    id_articulo:   Optional[str] = Field(default=None, max_length=20)   # referencia libre a la app Shein, sin FK real
    producto:      str = Field(max_length=60)
    tipo_producto: TipoProductoShein
    monto:         float

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


class SheinPedidoCreate(BaseModel):
    id_shein_cliente: int
    articulos:        list[SheinArticuloCreate]

    @field_validator("articulos")
    @classmethod
    def entre_1_y_4_articulos(cls, v: list[SheinArticuloCreate]) -> list[SheinArticuloCreate]:
        if not (1 <= len(v) <= 4):
            raise ValueError("Un pedido Shein debe tener entre 1 y 4 artículos")
        return v


class SheinArticuloRead(BaseModel):
    id_shein_articulo: int
    id_articulo:        Optional[str]
    producto:            str
    tipo_producto:        TipoProductoShein
    monto:                float
    monto_vigente:        Optional[float]
    estatus_articulo:     EstatusArticuloShein

    model_config = {"from_attributes": True}


class SheinArticuloEstatusUpdate(BaseModel):
    """Resuelve la confirmación del cliente ante variación de precio (o cancelación),
    previo a registrar el corte. REGLAS_NEGOCIO: cualquier variación de precio exige
    notificar al cliente y obtener confirmación explícita."""
    estatus_articulo: EstatusArticuloShein
    monto_vigente:     Optional[float] = None   # solo si el precio varió respecto al pedido

    @field_validator("monto_vigente")
    @classmethod
    def monto_vigente_positivo(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v <= 0:
            raise ValueError("monto_vigente debe ser mayor a 0")
        return v


class SheinPedidoRead(BaseModel):
    id_shein_pedido: int
    id_shein_cliente: int
    id_shein_corte:   Optional[int]
    estatus_pago:     Optional[EstatusPago]
    fecha:            date
    articulos:        list[SheinArticuloRead]
    monto_pedido:     float   # calculado: suma de artículos 'confirmado' (monto_vigente si aplica)

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────────────────────────────────────
# SHEIN CORTE
# ──────────────────────────────────────────────────────────────────────────

class SheinCorteCreate(BaseModel):
    fecha_corte:      date
    id_shein_pedidos: list[int]   # pedidos a incluir en este corte
    total_ticket:     float       # captura manual, pagado en OXXO

    @field_validator("id_shein_pedidos")
    @classmethod
    def al_menos_un_pedido(cls, v: list[int]) -> list[int]:
        if not v:
            raise ValueError("Debe incluir al menos un pedido en el corte")
        return v

    @field_validator("total_ticket")
    @classmethod
    def total_ticket_positivo(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("total_ticket debe ser mayor a 0")
        return v


class SheinCorteRead(BaseModel):
    id_shein_corte: int
    fecha_corte:     date
    total_pedidos:   int
    suma_pedidos:    float
    total_ticket:    float
    cupon:           float

    model_config = {"from_attributes": True}
