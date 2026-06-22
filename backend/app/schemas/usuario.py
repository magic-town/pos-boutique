from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import datetime


class UsuarioCreate(BaseModel):
    username: str
    password: str
    rol:      str = "estandar"

    @field_validator("username", "password")
    @classmethod
    def no_vacio(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Este campo no puede estar vacío")
        return v.strip()

    @field_validator("rol")
    @classmethod
    def rol_valido(cls, v: str) -> str:
        if v not in ("estandar", "admin"):
            raise ValueError("Rol debe ser 'estandar' o 'admin'")
        return v


class UsuarioRead(BaseModel):
    id_usuario:     int
    username:       str
    rol:            str
    activo:         str
    fecha_registro: Optional[datetime]

    model_config = {"from_attributes": True}
