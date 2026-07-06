from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional
from datetime import date
from app.models.models import FrecuenciaPago


class ClienteCreate(BaseModel):
    # INC-18 (hallazgo nuevo, ver docs/REPORT.md §4.3): ninguno de estos
    # campos tenía max_length alineado a los String(N) de models.py /
    # module_clientes.md. SQLite no lo habría rechazado en runtime (sin
    # enforcement real de VARCHAR(N)), pero el contrato del schema quedaba
    # roto en silencio — mismo tipo de brecha que se corrigió en Shein
    # (pedido_shein.py) para nombre/colonia/producto/id_articulo.
    nombre:       str = Field(max_length=40)
    colonia:      str = Field(max_length=20)
    telefono:     int
    ref_nombre:   str = Field(max_length=40)
    ref_colonia:  str = Field(max_length=40)
    ref_telefono: Optional[int] = None
    frecuencia_pago: FrecuenciaPago  # INC-02
    dia_pago_especifico: Optional[int] = None       # obligatorio solo si frecuencia_pago = dia_especifico_mes
    frecuencia_pago_detalle: Optional[str] = Field(default=None, max_length=60)   # obligatorio solo si frecuencia_pago = otro

    @field_validator("nombre", "colonia", "ref_nombre", "ref_colonia")
    @classmethod
    def no_vacio(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Este campo no puede estar vacío")
        return v.strip()

    @field_validator("telefono", "ref_telefono")
    @classmethod
    def diez_digitos(cls, v):
        if v is None:
            return v
        if len(str(v)) != 10:
            raise ValueError("El teléfono debe tener 10 dígitos")
        return v

    @field_validator("dia_pago_especifico")
    @classmethod
    def dia_en_rango(cls, v):
        if v is not None and not (1 <= v <= 31):
            raise ValueError("dia_pago_especifico debe estar entre 1 y 31")
        return v

    @model_validator(mode="after")
    def campos_condicionales_por_frecuencia(self):
        if self.frecuencia_pago == FrecuenciaPago.dia_especifico_mes and self.dia_pago_especifico is None:
            raise ValueError(
                "dia_pago_especifico es obligatorio cuando frecuencia_pago = 'dia_especifico_mes'"
            )
        if self.frecuencia_pago == FrecuenciaPago.otro and not (
            self.frecuencia_pago_detalle and self.frecuencia_pago_detalle.strip()
        ):
            raise ValueError(
                "frecuencia_pago_detalle es obligatorio cuando frecuencia_pago = 'otro'"
            )
        if self.frecuencia_pago_detalle:
            self.frecuencia_pago_detalle = self.frecuencia_pago_detalle.strip()
        return self


class ClienteRead(BaseModel):
    id_cliente:    int
    no_cliente:    str
    nombre:        str
    colonia:       str
    telefono:      int
    ref_nombre:    str
    ref_colonia:   str
    ref_telefono:  Optional[int]
    saldo:         float
    estatus:       str
    frecuencia_pago: FrecuenciaPago  # INC-02
    dia_pago_especifico: Optional[int]
    frecuencia_pago_detalle: Optional[str]
    fecha_pago_programada: Optional[date]  # INC-10 — Column(Date) en models.py
    fecha_registro: date  # corregido: Column(Date) en models.py, no nullable ahí

    model_config = {"from_attributes": True}


class ClienteResumen(BaseModel):
    """Vista compacta para búsquedas y selectores en el frontend."""
    id_cliente: int
    no_cliente: str
    nombre:     str
    colonia:    str
    saldo:      float
    estatus:    str

    model_config = {"from_attributes": True}
