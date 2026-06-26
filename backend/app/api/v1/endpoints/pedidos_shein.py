from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas.pedido_shein import PedidoSheinCreate, PedidoSheinRead
from app.services.pedido_shein_service import crear_pedido_shein, obtener_pedidos_shein_cliente
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/pedidos-shein", tags=["pedidos-shein"])


@router.post("", response_model=PedidoSheinRead, status_code=status.HTTP_201_CREATED)
def nuevo_pedido_shein(
    data: PedidoSheinCreate,
    db: Session = Depends(get_db),
    _: object = Depends(get_current_user),
):
    return crear_pedido_shein(db, data)


@router.get("/{id_cliente}", response_model=list[PedidoSheinRead])
def pedidos_shein_cliente(
    id_cliente: int,
    db: Session = Depends(get_db),
    _: object = Depends(get_current_user),
):
    return obtener_pedidos_shein_cliente(db, id_cliente)
