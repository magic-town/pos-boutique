from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas.pedido_shein import (
    SheinClienteCreate,
    SheinClienteRead,
    SheinPedidoCreate,
    SheinPedidoRead,
    SheinArticuloRead,
    SheinArticuloEstatusUpdate,
    SheinCorteCreate,
    SheinCorteRead,
)
from app.services import pedido_shein_service as service
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/shein", tags=["shein"])


# ── Flujo 1: Registrar Cliente Shein ───────────────────────────────────────

@router.post("/clientes", response_model=SheinClienteRead, status_code=status.HTTP_201_CREATED)
def registrar_shein_cliente(
    data: SheinClienteCreate,
    db: Session = Depends(get_db),
    _: object = Depends(get_current_user),
):
    return service.crear_shein_cliente(db, data)


@router.get("/clientes", response_model=list[SheinClienteRead])
def listar_shein_clientes(
    db: Session = Depends(get_db),
    _: object = Depends(get_current_user),
):
    return service.obtener_shein_clientes(db)


# ── Flujo 2: Registrar Pedido Shein ────────────────────────────────────────

@router.post("/pedidos", response_model=SheinPedidoRead, status_code=status.HTTP_201_CREATED)
def registrar_shein_pedido(
    data: SheinPedidoCreate,
    db: Session = Depends(get_db),
    _: object = Depends(get_current_user),
):
    return service.crear_shein_pedido(db, data)


# ── Flujo 3: Lista de Pedidos ───────────────────────────────────────────────

@router.get("/pedidos", response_model=list[SheinPedidoRead])
def listar_shein_pedidos(
    id_shein_cliente: int | None = None,
    sin_corte: bool = False,
    db: Session = Depends(get_db),
    _: object = Depends(get_current_user),
):
    return service.obtener_shein_pedidos(db, id_shein_cliente=id_shein_cliente, sin_corte=sin_corte)


# Soporte necesario para el flujo de corte: confirmar/cancelar un artículo
# ante variación de precio, antes de que el pedido pueda entrar a un corte.
@router.patch("/pedidos/articulos/{id_shein_articulo}", response_model=SheinArticuloRead)
def resolver_estatus_articulo(
    id_shein_articulo: int,
    data: SheinArticuloEstatusUpdate,
    db: Session = Depends(get_db),
    _: object = Depends(get_current_user),
):
    return service.actualizar_estatus_articulo(db, id_shein_articulo, data)


# ── Flujo 4: Registrar Corte ────────────────────────────────────────────────

@router.post("/cortes", response_model=SheinCorteRead, status_code=status.HTTP_201_CREATED)
def registrar_shein_corte(
    data: SheinCorteCreate,
    db: Session = Depends(get_db),
    _: object = Depends(get_current_user),
):
    return service.crear_shein_corte(db, data)


# ── Flujo 5: Consulta de Cortes ─────────────────────────────────────────────

@router.get("/cortes", response_model=list[SheinCorteRead])
def listar_shein_cortes(
    db: Session = Depends(get_db),
    _: object = Depends(get_current_user),
):
    return service.obtener_shein_cortes(db)


@router.get("/cortes/{id_shein_corte}", response_model=SheinCorteRead)
def detalle_shein_corte(
    id_shein_corte: int,
    db: Session = Depends(get_db),
    _: object = Depends(get_current_user),
):
    return service.obtener_shein_corte(db, id_shein_corte)
