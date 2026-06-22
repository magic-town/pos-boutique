from pydantic import BaseModel
from typing import Optional


class Token(BaseModel):
    """Respuesta del endpoint POST /auth/login."""
    access_token: str
    token_type:   str = "bearer"


class TokenData(BaseModel):
    """Payload decodificado del JWT — uso interno del backend."""
    username:  Optional[str] = None
    rol:       Optional[str] = None
