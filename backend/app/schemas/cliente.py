from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import datetime


class ClienteCreate(BaseModel):
    nombre:       str
    colonia:      str
    telefono:     str
    ref_nombre:   str
    ref_colonia:  str
    ref_telefono: Optional[str] = None

    @field_validator("nombre", "colonia", "telefono", "ref_nombre", "ref_colonia")
    @classmethod
    def no_vacio(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Este campo no puede estar vacío")
        return v.strip()


class ClienteRead(BaseModel):
    id_cliente:    int
    no_cliente:    str
    nombre:        str
    colonia:       str
    telefono:      str
    ref_nombre:    str
    ref_colonia:   str
    ref_telefono:  Optional[str]
    saldo:         float
    estatus:       str
    fecha_registro: Optional[datetime]

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
