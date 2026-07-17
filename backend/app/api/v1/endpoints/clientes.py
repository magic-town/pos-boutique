from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas.cliente import (
    ClienteCreate,
    ClienteRead,
    ClienteResumen,
    CarteraVencidaRead,
    FamiliarVincular,
    FamiliarRead,
)
from app.services.cliente_service import (
    crear_cliente,
    buscar_clientes,
    obtener_cliente,
    calcular_bandera_naranja,
    calcular_bandera_amarilla,
    calcular_bandera_roja,
    calcular_bandera_negra,
    cancelar_cliente,
    listar_familiares,
    vincular_familiar,
    desvincular_familiar,
)
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/clientes", tags=["clientes"])


def _asignar_banderas(db: Session, cliente):
    """Calcula y asigna las 4 banderas (module_clientes.md §Sistema de
    banderas) sobre el objeto Cliente antes de serializarlo con
    ClienteRead. bandera_negra depende de bandera_roja de los familiares,
    no de la del propio cliente en esta función -- eso ya lo resuelve
    calcular_bandera_negra() internamente."""
    cliente.bandera_amarilla = calcular_bandera_amarilla(cliente)
    cliente.bandera_roja = calcular_bandera_roja(cliente)
    cliente.bandera_naranja = calcular_bandera_naranja(db, cliente)
    cliente.bandera_negra = calcular_bandera_negra(db, cliente)
    return cliente


@router.post("", response_model=ClienteRead, status_code=status.HTTP_201_CREATED)
def registrar_cliente(
    data: ClienteCreate,
    db: Session = Depends(get_db),
    _: object = Depends(get_current_user),
):
    cliente = crear_cliente(db, data)
    return _asignar_banderas(db, cliente)


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
    return _asignar_banderas(db, cliente)


@router.post("/{id_cliente}/cancelar", response_model=CarteraVencidaRead, status_code=status.HTTP_200_OK)
def cancelar_cliente_endpoint(
    id_cliente: int,
    db: Session = Depends(get_db),
    _: object = Depends(get_current_user),
):
    if obtener_cliente(db, id_cliente) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente no encontrado")
    try:
        return cancelar_cliente(db, id_cliente)
    except ValueError as e:
        # Precondición de negocio (bandera_roja) no cumplida, no un 404.
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{id_cliente}/familiares", response_model=list[FamiliarRead])
def listar_familiares_endpoint(
    id_cliente: int,
    db: Session = Depends(get_db),
    _: object = Depends(get_current_user),
):
    if obtener_cliente(db, id_cliente) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente no encontrado")
    return listar_familiares(db, id_cliente)


@router.post("/{id_cliente}/familiares", response_model=FamiliarRead, status_code=status.HTTP_201_CREATED)
def vincular_familiar_endpoint(
    id_cliente: int,
    data: FamiliarVincular,
    db: Session = Depends(get_db),
    _: object = Depends(get_current_user),
):
    try:
        vinculo = vincular_familiar(db, id_cliente, data.id_cliente_relacionado)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    otro = vinculo.cliente_b if vinculo.id_cliente_a == id_cliente else vinculo.cliente_a
    return {
        "id_vinculo": vinculo.id_vinculo,
        "id_cliente": id_cliente,
        "id_cliente_relacionado": otro.id_cliente,
        "nombre_relacionado": otro.nombre,
        "no_cliente_relacionado": otro.no_cliente,
    }


@router.delete("/{id_cliente}/familiares/{id_vinculo}", status_code=status.HTTP_204_NO_CONTENT)
def desvincular_familiar_endpoint(
    id_cliente: int,
    id_vinculo: int,
    db: Session = Depends(get_db),
    _: object = Depends(get_current_user),
):
    try:
        desvincular_familiar(db, id_cliente, id_vinculo)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# NOTA (revisión de negocio, ver conversación con el usuario): se quitó el
# endpoint PATCH /{id_cliente}/rehabilitar y no se repone. `estatus` no es
# un campo editable por la operadora bajo ninguna forma -- ni aquí ni desde
# "Editar Cliente" -- es un campo derivado de `saldo`, sincronizado en
# automático por cliente_service.sincronizar_estatus() en cada punto del
# sistema que modifica el saldo del cliente (Pedidos, Movimientos). No debe
# volver a aparecer como campo capturable en ningún formulario ni endpoint.
