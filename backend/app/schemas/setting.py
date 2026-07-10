from pydantic import BaseModel, field_validator


class ConfiguracionRead(BaseModel):
    clave: str
    valor: str

    model_config = {"from_attributes": True}


class ConfiguracionUpdate(BaseModel):
    valor: str


class UsuarioCambiarPassword(BaseModel):
    password: str

    # Misma regla que UsuarioCreate.password en app/schemas/usuario.py.
    # Duplicada a propósito para MVP (esqueleto funcional); si el módulo
    # crece, mover a un validador compartido.
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


class UsuarioCambiarRol(BaseModel):
    rol: str

    @field_validator("rol")
    @classmethod
    def rol_valido(cls, v: str) -> str:
        if v not in ("estandar", "admin"):
            raise ValueError("Rol debe ser 'estandar' o 'admin'")
        return v
