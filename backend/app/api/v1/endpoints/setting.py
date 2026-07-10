from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.models import Usuario, Configuracion
from app.schemas.usuario import UsuarioCreate, UsuarioRead
from app.schemas.setting import (
    ConfiguracionRead,
    ConfiguracionUpdate,
    UsuarioCambiarPassword,
    UsuarioCambiarRol,
)
from app.services.auth_service import (
    get_current_user,
    crear_usuario,
    hash_password,
    obtener_usuario,
)

router = APIRouter(prefix="/setting", tags=["Setting"])

# Claves booleanas ('0'/'1') de la sección "Métodos de pago" del spec.
CLAVES_METODOS_PAGO = {
    "pago_efectivo_activo",
    "pago_transferencia_activo",
    "pago_tarjeta_debito_activo",
    "pago_tarjeta_credito_activo",
    "pago_msi_activo",
    "pago_vales_activo",
}

# Efectivo: "activo, no desactivable" según module_setting.md.
CLAVES_NO_DESACTIVABLES = {"pago_efectivo_activo"}


# ──────────────────────────────────────────────────────────────────────────
# Usuarios
# ──────────────────────────────────────────────────────────────────────────

@router.post("/usuarios", response_model=UsuarioRead, status_code=status.HTTP_201_CREATED)
def agregar_usuario(
    datos: UsuarioCreate,
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(get_current_user),
):
    if obtener_usuario(db, datos.usuario):
        raise HTTPException(status_code=409, detail="El usuario ya existe")
    return crear_usuario(db, datos.usuario, datos.password, datos.rol)


@router.patch("/usuarios/{id_usuario}/password", response_model=UsuarioRead)
def cambiar_password(
    id_usuario: int,
    datos: UsuarioCambiarPassword,
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(get_current_user),
):
    user = db.get(Usuario, id_usuario)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    user.password_hash = hash_password(datos.password)
    db.commit()
    db.refresh(user)
    return user


@router.patch("/usuarios/{id_usuario}/rol", response_model=UsuarioRead)
def cambiar_rol(
    id_usuario: int,
    datos: UsuarioCambiarRol,
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(get_current_user),
):
    # Nota del spec: "solo edición de enum; sin lógica de permisos
    # diferenciada en MVP" — no se valida aquí si usuario_actual es admin.
    user = db.get(Usuario, id_usuario)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    user.rol = datos.rol
    db.commit()
    db.refresh(user)
    return user


# ──────────────────────────────────────────────────────────────────────────
# Información del sistema
# ──────────────────────────────────────────────────────────────────────────

@router.get("/zona-horaria")
def obtener_zona_horaria(
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(get_current_user),
):
    # Solo lectura / informativo, per spec. Se lee de la tabla configuracion
    # (seed: 'America/Mexico_City'), no del reloj del sistema operativo en
    # tiempo de ejecución -- ver nota en el mensaje de respuesta.
    config = db.get(Configuracion, "zona_horaria")
    return {"zona_horaria": config.valor if config else None}


# ──────────────────────────────────────────────────────────────────────────
# Configuración general (métodos de pago, etc.)
# ──────────────────────────────────────────────────────────────────────────

@router.get("/configuracion", response_model=List[ConfiguracionRead])
def listar_configuracion(
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(get_current_user),
):
    return db.query(Configuracion).all()


@router.patch("/configuracion/{clave}", response_model=ConfiguracionRead)
def actualizar_configuracion(
    clave: str,
    datos: ConfiguracionUpdate,
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(get_current_user),
):
    config = db.get(Configuracion, clave)
    if not config:
        raise HTTPException(status_code=404, detail="Clave de configuración no encontrada")

    if clave in CLAVES_METODOS_PAGO and datos.valor not in ("0", "1"):
        raise HTTPException(
            status_code=422, detail="El valor debe ser '0' (inactivo) o '1' (activo)"
        )
    if clave in CLAVES_NO_DESACTIVABLES and datos.valor == "0":
        raise HTTPException(status_code=409, detail="Efectivo no puede desactivarse")

    config.valor = datos.valor
    db.commit()
    db.refresh(config)
    return config
