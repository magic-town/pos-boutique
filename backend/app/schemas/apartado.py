"""
Schemas del módulo Apartado (REGLAS_NEGOCIO.md §5, module_movimientos.md).

Apartado no es un módulo independiente -- es una operación del Panel Principal
(igual que Contado/Abono/Gasto), pero con su propia cabecera+detalle
(apartados / apartados_articulos), por lo que se separa de movimiento.py en
su propio archivo de schemas -- mismo criterio de separación que pedido.py
tiene respecto a movimiento.py.
"""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.models import EstatusApartado, EstatusApartadoArticulo, FormaPago


# ──────────────────────────────────────────────────────────────────────────
# Artículo — creación
# ──────────────────────────────────────────────────────────────────────────

class ApartadoArticuloCreate(BaseModel):
    """Un renglón de apartados_articulos.

    precio_producto es solo-lectura en el frontend cuando id_producto tiene
    coincidencia en inventario (autollenado, module_movimientos.md regla 3) --
    la resolución real (¿existe el id_producto?, ¿qué precio_venta tiene?)
    requiere DB y vive en el service, mismo patrón que _resolver_monto en
    pedido_service.py. Este schema solo puede validar la regla que no
    depende de la base: si no hay id_producto, no hay posibilidad de
    autollenado, así que el precio manual es obligatorio.
    """

    id_producto: Optional[int] = None
    precio_producto: Optional[float] = None

    @model_validator(mode="after")
    def _precio_manual_obligatorio_sin_id_producto(self):
        if self.id_producto is None and self.precio_producto is None:
            raise ValueError(
                "precio_producto es obligatorio cuando no se captura id_producto "
                "(sin id_producto no hay lookup posible en inventario)."
            )
        return self


class ApartadoCreate(BaseModel):
    """Cabecera + lista de artículos del lote (module_movimientos.md,
    'Comportamiento -- Registrar Apartado').

    id_cliente ya resuelto (no no_cliente) -- consistente con MovimientoCreate:
    Apartado comparte el mismo campo "No. Cliente" input_lookup del Panel
    Principal que Contado/Abono/Gasto, y el frontend ya resuelve
    no_cliente -> id_cliente antes de enviar en esos tres. Cliente obligatorio
    (REGLAS_NEGOCIO.md §5, regla 1 de Apartado).
    """

    id_cliente: int
    articulos: list[ApartadoArticuloCreate] = Field(min_length=1)
    monto_primer_pago: float
    forma_pago: FormaPago

    @field_validator("monto_primer_pago")
    @classmethod
    def _minimo_100(cls, v: float) -> float:
        # REGLAS_NEGOCIO.md §5, regla 3 -- único para todo el lote, no por artículo.
        if v < 100:
            raise ValueError(
                "monto_primer_pago debe ser de al menos $100.00 (cubre todo el lote, "
                "no por artículo)."
            )
        return v


# ──────────────────────────────────────────────────────────────────────────
# Artículo — lectura
# ──────────────────────────────────────────────────────────────────────────

class ApartadoArticuloRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_apartado_articulo: int
    id_apartado: int
    id_producto: Optional[int] = None
    precio_producto: float
    estatus_articulo: EstatusApartadoArticulo


class ApartadoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_apartado: int
    id_cliente: int
    fecha_apartado: datetime
    monto_primer_pago: float
    saldo_pendiente: float
    estatus: EstatusApartado
    articulos: list[ApartadoArticuloRead] = []


# ──────────────────────────────────────────────────────────────────────────
# Cancelar artículo de un apartado
# (module_movimientos.md, 'Comportamiento -- Cancelar artículo de un Apartado')
# ──────────────────────────────────────────────────────────────────────────

class ApartadoArticuloCancelableOut(BaseModel):
    """Renglón de 'Selecciona el artículo a cancelar' dentro del apartado
    abierto del cliente."""
    model_config = ConfigDict(from_attributes=True)

    id_apartado_articulo: int
    id_producto: Optional[int] = None
    precio_producto: float


class ApartadoCancelacionConfirmar(BaseModel):
    id_apartado_articulo: int


# ──────────────────────────────────────────────────────────────────────────
# Consulta -- apartado abierto del cliente
# (usado por Abono/Panel Principal para mostrar saldo_pendiente en vivo,
# module_movimientos.md 'Comportamiento -- Abonar / Liquidar' paso 1)
# ──────────────────────────────────────────────────────────────────────────

class ApartadoAbiertoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_apartado: int
    fecha_apartado: datetime
    saldo_pendiente: float
