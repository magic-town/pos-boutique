"""
Schemas del módulo Pedidos (REGLAS_NEGOCIO.md §3, module_pedidos.md).

Reemplaza por completo el schema plano anterior (app/schemas/pedido.py viejo,
con opcion_*) -- REPORT.md §4.1 confirma que no hay nada reutilizable de ahí.
"""

from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.models import EstatusArticulo, Proveedor, RolArticulo, TipoProducto


# ──────────────────────────────────────────────────────────────────────────
# Artículo — creación
# ──────────────────────────────────────────────────────────────────────────

class ArticuloCreate(BaseModel):
    """Un renglón de pedidos_articulos. Se usa tanto para 'principal' como
    para 'alternativa' -- el rol lo decide quien construye el payload
    (ArticuloConAlternativa), no este schema."""

    tipo_producto: TipoProducto
    proveedor: Optional[Proveedor] = None
    id_producto: Optional[str] = Field(default=None, max_length=12)
    producto: str = Field(max_length=40)
    marca: Optional[str] = Field(default=None, max_length=20)
    talla: Optional[str] = Field(default=None, max_length=8)
    monto: Optional[float] = None
    # Solo se envía en el artículo sustituto de una devolución (module_pedidos.md,
    # precarga de ventana_registrar_pedido). NULL en todos los demás casos.
    id_articulo_sustituye: Optional[int] = None

    @model_validator(mode="after")
    def _validar_reglas_por_tipo(self):
        if self.tipo_producto == TipoProducto.informal:
            # proveedor / id_producto deshabilitados para informal -- se
            # limpian aunque el cliente los haya enviado (module_pedidos.md,
            # tabla "Comportamiento por tipo_producto").
            self.proveedor = None
            self.id_producto = None
        else:  # formal
            if self.proveedor is None:
                raise ValueError("proveedor es obligatorio cuando tipo_producto = 'formal'.")
            if self.proveedor == Proveedor.otro and self.monto is None:
                raise ValueError(
                    "monto es obligatorio cuando tipo_producto = 'formal' y proveedor = 'otro' "
                    "(sin catálogo digitalizado, captura manual)."
                )
        return self


class ArticuloConAlternativa(BaseModel):
    """Un 'slot' del formulario: artículo principal + alternativa opcional."""

    principal: ArticuloCreate
    alternativa: Optional[ArticuloCreate] = None


class PedidoCreate(BaseModel):
    no_cliente: str
    articulos: list[ArticuloConAlternativa] = Field(min_length=1, max_length=4)


# ──────────────────────────────────────────────────────────────────────────
# Artículo — lectura
# ──────────────────────────────────────────────────────────────────────────

class ArticuloRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_articulo: int
    id_pedido: int
    rol: RolArticulo
    id_articulo_principal: Optional[int] = None
    tipo_producto: TipoProducto
    proveedor: Optional[Proveedor] = None
    id_producto: Optional[str] = None
    producto: str
    marca: Optional[str] = None
    talla: Optional[str] = None
    monto: Optional[float] = None
    estatus_articulo: EstatusArticulo
    id_articulo_sustituye: Optional[int] = None


class PedidoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_pedido: int
    id_cliente: int
    fecha: date
    articulos: list[ArticuloRead] = []


# ──────────────────────────────────────────────────────────────────────────
# Lookup de precio (autollenado en vivo desde el formulario)
# ──────────────────────────────────────────────────────────────────────────

class MontoLookupOut(BaseModel):
    encontrado: bool
    monto: Optional[float] = None


# ──────────────────────────────────────────────────────────────────────────
# Registrar Devolución
# ──────────────────────────────────────────────────────────────────────────

class ArticuloDevolvibleOut(BaseModel):
    """Renglón de la tabla 'Selecciona el artículo a devolver'
    (module_pedidos.md, paso_2 de ventana_registrar_devolucion)."""
    model_config = ConfigDict(from_attributes=True)

    id_articulo: int
    fecha: date
    tipo_producto: TipoProducto
    proveedor: Optional[Proveedor] = None
    producto: str
    marca: Optional[str] = None
    talla: Optional[str] = None
    monto: Optional[float] = None


class DevolucionConfirmar(BaseModel):
    no_cliente: str
    id_articulo: int


class DevolucionPrecarga(BaseModel):
    """Lo que el frontend usa para pre-cargar ventana_registrar_pedido
    tras confirmar la devolución."""
    tipo_producto: TipoProducto
    proveedor: Optional[Proveedor] = None
    marca: Optional[str] = None
    talla: Optional[str] = None
    id_articulo_sustituye: int


# ──────────────────────────────────────────────────────────────────────────
# Cancelar Artículo
# ──────────────────────────────────────────────────────────────────────────

class ArticuloCancelableOut(BaseModel):
    """Renglón de 'Selecciona el artículo a cancelar' -- incluye
    estatus_articulo porque determina si hay reversión de saldo."""
    model_config = ConfigDict(from_attributes=True)

    id_articulo: int
    fecha: date
    producto: str
    marca: Optional[str] = None
    talla: Optional[str] = None
    proveedor: Optional[Proveedor] = None
    monto: Optional[float] = None
    estatus_articulo: EstatusArticulo


class CancelacionConfirmar(BaseModel):
    no_cliente: str
    id_articulo: int


# ──────────────────────────────────────────────────────────────────────────
# Lista de Surtido
# ──────────────────────────────────────────────────────────────────────────

class ListaSurtidoItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_articulo: int
    no_cliente: str
    nombre: str
    rol: RolArticulo
    producto: str
    marca: Optional[str] = None
    talla: Optional[str] = None
    proveedor: Optional[Proveedor] = None
    id_producto: Optional[str] = None
    monto: Optional[float] = None
    fecha: date


class ValidarClienteOut(BaseModel):
    no_cliente: str
    nombre: str
