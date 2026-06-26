from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas.pedido import PedidoCreate, PedidoRead
from app.services.pedido_service import crear_pedido, obtener_pedidos_cliente
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/pedidos", tags=["pedidos"])


@router.post("", response_model=PedidoRead, status_code=status.HTTP_201_CREATED)
def nuevo_pedido(
    data: PedidoCreate,
    db: Session = Depends(get_db),
    _: object = Depends(get_current_user),
):
    return crear_pedido(db, data)


@router.get("/{id_cliente}", response_model=list[PedidoRead])
def pedidos_cliente(
    id_cliente: int,
    db: Session = Depends(get_db),
    _: object = Depends(get_current_user),
):
    return obtener_pedidos_cliente(db, id_cliente)
