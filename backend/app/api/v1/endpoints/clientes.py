from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas.cliente import ClienteCreate, ClienteRead, ClienteResumen
from app.services.cliente_service import crear_cliente, buscar_clientes, obtener_cliente
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/clientes", tags=["clientes"])


@router.post("", response_model=ClienteRead, status_code=status.HTTP_201_CREATED)
def registrar_cliente(
    data: ClienteCreate,
    db: Session = Depends(get_db),
    _: object = Depends(get_current_user),
):
    return crear_cliente(db, data)


@router.get("", response_model=list[ClienteResumen])
def listar_clientes(
    q: str = Query(default="", description="Buscar por nombre o no_cliente"),
    db: Session = Depends(get_db),
    _: object = Depends(get_current_user),
):
    return buscar_clientes(db, q)


@router.get("/{id_cliente}", response_model=ClienteRead)
def detalle_cliente(
    id_cliente: int,
    db: Session = Depends(get_db),
    _: object = Depends(get_current_user),
):
    cliente = obtener_cliente(db, id_cliente)
    if not cliente:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente no encontrado")
    return cliente

# NOTA (revisión de negocio, ver conversación con el usuario): se quitó el
# endpoint PATCH /{id_cliente}/rehabilitar. module_clientes.md no define
# ninguna opción de "Rehabilitar Cliente" -- el menú de Clientes solo tiene
# 4 botones (Registrar, Editar, Consulta Cliente, Consulta Historial), y el
# spec de `estatus` es explícito: el cambio, en cualquier dirección
# (activo <-> inactivo), lo hace la operadora manualmente desde "Editar
# Cliente" (UPDATE genérico, Opción 2 -- todavía sin construir). No hay
# regla de negocio que dependa de un endpoint de rehabilitación aparte;
# `saldo = 0` tampoco dispara nada automático. Si `cliente_service.py`
# todavía tiene la función `rehabilitar_cliente()`, también se puede
# eliminar de ahí -- no queda ningún caller.
