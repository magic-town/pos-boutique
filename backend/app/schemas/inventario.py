"""
Schemas del módulo Inventario (FULLSTACK/module_inventario.md).

Primera implementación de código de este módulo -- el modelo SQLAlchemy
(Inventario, en models.py) ya existía, sin usarse desde ningún endpoint.
"""

from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.models import CategoriaInventario, EstatusInventario, TipoProducto


# ──────────────────────────────────────────────────────────────────────────
# Opción 1 — Agregar Producto
# ──────────────────────────────────────────────────────────────────────────

class ProductoCreate(BaseModel):
    categoria: CategoriaInventario
    tipo_producto: TipoProducto
    descripcion: str = Field(max_length=40)
    talla: Optional[str] = Field(default=None, max_length=10)
    color: Optional[str] = Field(default=None, max_length=10)
    marca: Optional[str] = Field(default=None, max_length=20)
    precio_venta: int
    stock: int = 0


class ProductoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_producto: int
    categoria: CategoriaInventario
    tipo_producto: TipoProducto
    descripcion: str
    talla: Optional[str] = None
    color: Optional[str] = None
    marca: Optional[str] = None
    precio_venta: int
    precio_descuento: Optional[int] = None
    stock: int
    estatus: EstatusInventario
    descripcion_ruta: Optional[str] = None
    created: date
    changed_status: Optional[date] = None


# ──────────────────────────────────────────────────────────────────────────
# Opción 2 — Cambiar Estatus
# ──────────────────────────────────────────────────────────────────────────

# Transiciones válidas (module_inventario.md, Enum estatus).
TRANSICIONES_VALIDAS: dict[EstatusInventario, set[EstatusInventario]] = {
    EstatusInventario.disponible: {
        EstatusInventario.en_ruta, EstatusInventario.disponible_c_descuento,
        EstatusInventario.apartado, EstatusInventario.vendido,
    },
    EstatusInventario.disponible_c_descuento: {
        EstatusInventario.disponible, EstatusInventario.en_ruta,
        EstatusInventario.apartado, EstatusInventario.vendido,
    },
    EstatusInventario.en_ruta: {EstatusInventario.disponible, EstatusInventario.vendido},
    EstatusInventario.apartado: {EstatusInventario.disponible, EstatusInventario.vendido},
    EstatusInventario.vendido: set(),
}


class CambiarEstatusRequest(BaseModel):
    nuevo_estatus: EstatusInventario
    # Condicional según nuevo_estatus (module_inventario.md Opción 2):
    descripcion_ruta: Optional[str] = None            # requerido si nuevo_estatus = en_ruta
    precio_descuento: Optional[int] = None            # requerido si nuevo_estatus = disponible_c_descuento

    @model_validator(mode="after")
    def _validar_campos_condicionales(self):
        if self.nuevo_estatus == EstatusInventario.en_ruta and not self.descripcion_ruta:
            raise ValueError("descripcion_ruta es obligatoria cuando nuevo_estatus = 'en_ruta'.")
        if self.nuevo_estatus == EstatusInventario.disponible_c_descuento and self.precio_descuento is None:
            raise ValueError("precio_descuento es obligatorio cuando nuevo_estatus = 'disponible_c/descuento'.")
        return self


# ──────────────────────────────────────────────────────────────────────────
# Opción 3 — Consulta Inventario
# ──────────────────────────────────────────────────────────────────────────

class InventarioFiltro(BaseModel):
    categoria: Optional[CategoriaInventario] = None
    tipo_producto: Optional[TipoProducto] = None
    estatus: Optional[EstatusInventario] = None
    marca: Optional[str] = None


# ──────────────────────────────────────────────────────────────────────────
# Opción 4 / 5 — Descuento Masivo (aplicar / retirar)
# ──────────────────────────────────────────────────────────────────────────

class SegmentoDescuento(BaseModel):
    """Segmento de productos objetivo. Filtro y selección manual no son
    excluyentes: si se dan ambos, se combinan con AND (selección manual
    dentro del resultado ya filtrado)."""

    categoria: Optional[CategoriaInventario] = None
    tipo_producto: Optional[TipoProducto] = None
    marca: Optional[str] = None
    talla: Optional[str] = None
    color: Optional[str] = None
    ids_producto: Optional[list[int]] = None

    @model_validator(mode="after")
    def _requiere_al_menos_un_criterio(self):
        criterios = [self.categoria, self.tipo_producto, self.marca, self.talla, self.color, self.ids_producto]
        if all(c is None for c in criterios):
            raise ValueError(
                "Se requiere al menos un criterio de segmento (filtro de campo o ids_producto) "
                "-- un descuento masivo sin ningún filtro afectaría todo el inventario."
            )
        return self


class AplicarDescuentoMasivoRequest(BaseModel):
    segmento: SegmentoDescuento
    pct: Optional[float] = Field(default=None, gt=0, lt=100)
    precio_fijo: Optional[int] = Field(default=None, gt=0)

    @model_validator(mode="after")
    def _exactamente_una_forma_de_descuento(self):
        if (self.pct is None) == (self.precio_fijo is None):
            raise ValueError("Especifica exactamente uno de 'pct' o 'precio_fijo', no ambos ni ninguno.")
        return self


class RetirarDescuentoMasivoRequest(BaseModel):
    segmento: SegmentoDescuento


class DescuentoMasivoResultado(BaseModel):
    productos_afectados: int
    productos_omitidos: list[int] = []  # ids omitidos por precio_fijo >= precio_venta
