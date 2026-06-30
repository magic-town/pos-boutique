from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas.token import Token
from app.services.auth_service import autenticar_usuario, crear_token

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=Token)
def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    # form.username es el campo estándar de OAuth2PasswordRequestForm (no tocar,
    # es de FastAPI/OAuth2, no de nuestro modelo Usuario).
    usuario = autenticar_usuario(db, form.username, form.password)
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # Antes: usuario.username -> ya no existe en el modelo (renombrado a Usuario.usuario)
    token = crear_token({"sub": usuario.usuario, "rol": usuario.rol})
    return {"access_token": token, "token_type": "bearer"}
