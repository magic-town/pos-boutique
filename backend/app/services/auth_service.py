from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import get_db
from app.models.models import Usuario
from app.schemas.token import TokenData

# ── Configuración ─────────────────────────────────────────────────────────────
# SECRET_KEY, ALGORITHM y TOKEN_EXPIRY_HOURS ya NO viven aquí hardcodeados.
# Vienen de app/core/config.py (settings), que a su vez lee .env si existe.
SECRET_KEY          = settings.SECRET_KEY
ALGORITHM           = settings.ALGORITHM
TOKEN_EXPIRY_HOURS  = settings.TOKEN_EXPIRY_HOURS

pwd_context   = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


# ── Password ──────────────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verificar_password(password_plano: str, hashed: str) -> bool:
    return pwd_context.verify(password_plano, hashed)


# ── JWT ───────────────────────────────────────────────────────────────────────

def crear_token(data: dict, expiry: Optional[timedelta] = None) -> str:
    payload = data.copy()
    expira = datetime.utcnow() + (expiry or timedelta(hours=TOKEN_EXPIRY_HOURS))
    payload.update({"exp": expira})
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


# ── Usuario ───────────────────────────────────────────────────────────────────
# Renombrado: Usuario.username -> Usuario.usuario
#             Usuario.hashed_password -> Usuario.password_hash
#             Usuario.activo: "true"/"false" (str) -> 1/0 (int)
# Alineado a app/models/models.py (propuesto, validado por el usuario).

def obtener_usuario(db: Session, usuario: str) -> Usuario | None:
    return db.query(Usuario).filter(Usuario.usuario == usuario).first()


def autenticar_usuario(db: Session, usuario: str, password: str) -> Usuario | None:
    user = obtener_usuario(db, usuario)
    if not user:
        return None
    if not verificar_password(password, user.password_hash):
        return None
    if not user.activo:
        return None
    return user


def crear_usuario(db: Session, usuario: str, password: str, rol: str = "estandar") -> Usuario:
    user = Usuario(
        usuario=usuario,
        password_hash=hash_password(password),
        rol=rol,
        activo=1,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


# ── Dependency — protege endpoints ────────────────────────────────────────────

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Usuario:
    """
    Dependency de FastAPI. Úsala en cualquier endpoint que requiera autenticación:

        @router.get("/ruta-protegida")
        def ruta(usuario: Usuario = Depends(get_current_user)):
            ...
    """
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token inválido o expirado",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        usuario = payload.get("sub")
        rol     = payload.get("rol")
        if usuario is None:
            raise credentials_error
        token_data = TokenData(username=usuario, rol=rol)
    except JWTError:
        raise credentials_error

    user = obtener_usuario(db, token_data.username)
    if not user or not user.activo:
        raise credentials_error
    return user
