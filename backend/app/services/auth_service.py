from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.models import Usuario
from app.schemas.token import TokenData

# ── Configuración ─────────────────────────────────────────────────────────────
# En producción SECRET_KEY debe vivir en .env — por ahora valor fijo para MVP.
# Rotar esta clave invalida todos los tokens activos.
SECRET_KEY    = "pos-boutique-secret-key-cambiar-en-produccion"
ALGORITHM     = "HS256"
TOKEN_EXPIRY_HOURS = 8  # sesión de una jornada laboral

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

def obtener_usuario(db: Session, username: str) -> Usuario | None:
    return db.query(Usuario).filter(Usuario.username == username).first()


def autenticar_usuario(db: Session, username: str, password: str) -> Usuario | None:
    usuario = obtener_usuario(db, username)
    if not usuario:
        return None
    if not verificar_password(password, usuario.hashed_password):
        return None
    if usuario.activo != "true":
        return None
    return usuario


def crear_usuario(db: Session, username: str, password: str, rol: str = "estandar") -> Usuario:
    usuario = Usuario(
        username=username,
        hashed_password=hash_password(password),
        rol=rol,
        activo="true",
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return usuario


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
        payload  = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        rol      = payload.get("rol")
        if username is None:
            raise credentials_error
        token_data = TokenData(username=username, rol=rol)
    except JWTError:
        raise credentials_error

    usuario = obtener_usuario(db, token_data.username)
    if not usuario or usuario.activo != "true":
        raise credentials_error
    return usuario
