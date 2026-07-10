from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import datetime


class UsuarioCreate(BaseModel):
    usuario:  str
    password: str
    rol:      str = "estandar"

    @field_validator("usuario")
    @classmethod
    def validar_usuario(cls, v: str) -> str:
        v = v.strip() if v else v
        if not v:
            raise ValueError("El usuario no puede estar vacío")
        if " " in v:
            raise ValueError("El usuario no puede contener espacios")
        if not (4 <= len(v) <= 16):
            raise ValueError("El usuario debe tener entre 4 y 16 caracteres")
        return v

    @field_validator("password")
    @classmethod
    def validar_password(cls, v: str) -> str:
        v = v.strip() if v else v
        if not v:
            raise ValueError("La contraseña no puede estar vacía")
        if not (4 <= len(v) <= 10):
            raise ValueError("La contraseña debe tener entre 4 y 10 caracteres")
        if not any(c.isupper() for c in v):
            raise ValueError("La contraseña debe tener al menos una mayúscula")
        return v

    @field_validator("rol")
    @classmethod
    def rol_valido(cls, v: str) -> str:
        if v not in ("estandar", "admin"):
            raise ValueError("Rol debe ser 'estandar' o 'admin'")
        return v


class UsuarioRead(BaseModel):
    id_usuario:     int
    usuario:        str
    rol:            str
    activo:         int
    fecha_registro: Optional[datetime]

    model_config = {"from_attributes": True}
