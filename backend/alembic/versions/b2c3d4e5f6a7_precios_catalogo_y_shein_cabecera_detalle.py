"""precios_catalogo nuevo + Shein reestructurado a cabecera-detalle

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-07-01

Ver docs/REPORT.md §2a y §2b (diseño cerrado). Cambios:
- precios_catalogo: tabla NUEVA.
- shein_pedidos_articulos: tabla NUEVA (detalle).
- shein_pedidos: deja de ser plana — se quitan producto/monto/monto_vigente
  (se mueven a shein_pedidos_articulos), se agrega estatus_pago.
- shein_cortes: suma_montos -> suma_pedidos; se elimina porcentaje_bono;
  bono_monto -> cupon; se agrega total_ticket.

NOTA: esta migración NO preserva datos existentes en las columnas eliminadas
de shein_pedidos (producto/monto/monto_vigente) — asume, igual que la
migración inicial, que no hay datos reales de Shein todavía. Confirmar antes
de correr en un pos.db con datos de prueba que se quieran conservar.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── precios_catalogo (NUEVA) ────────────────────────────────────────────
    op.create_table(
        'precios_catalogo',
        sa.Column('id_precio', sa.Integer(), nullable=False),
        sa.Column('proveedor', sa.Enum(
            'Price_Shoes', 'Pakar', 'Cklass', name='proveedorcatalogo'), nullable=False),
        sa.Column('id_producto', sa.String(length=12), nullable=False),
        sa.Column('precio_venta', sa.Integer(), nullable=False),
        sa.Column('fecha_catalogo', sa.Date(), nullable=False),
        sa.Column('catalogo', sa.String(), nullable=True),
        sa.Column('temporada', sa.String(), nullable=True),
        sa.Column('pagina', sa.Integer(), nullable=True),
        sa.Column('precio_base', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id_precio'),
    )
    op.create_index(op.f('ix_precios_catalogo_id_precio'), 'precios_catalogo', ['id_precio'], unique=False)

    # ── shein_cortes (CAMBIA columnas) ──────────────────────────────────────
    with op.batch_alter_table('shein_cortes', recreate='always') as batch_op:
        batch_op.add_column(sa.Column('total_ticket', sa.Float(), nullable=False, server_default='0'))
        batch_op.alter_column('suma_montos', new_column_name='suma_pedidos')
        batch_op.alter_column('bono_monto', new_column_name='cupon')
        batch_op.drop_column('porcentaje_bono')

    # server_default='0' fue solo para poder agregar la columna NOT NULL sobre
    # una tabla que puede tener filas; se retira, la columna queda obligatoria
    # sin default para inserts nuevos (el backend siempre la captura).
    with op.batch_alter_table('shein_cortes', recreate='always') as batch_op:
        batch_op.alter_column('total_ticket', server_default=None)

    # ── shein_pedidos (CAMBIA: deja de ser plana, pasa a cabecera) ──────────
    with op.batch_alter_table('shein_pedidos', recreate='always') as batch_op:
        batch_op.add_column(sa.Column('estatus_pago', sa.Enum(
            'pago_pendiente', 'pagado', name='estatuspago'), nullable=True))
        batch_op.drop_column('producto')
        batch_op.drop_column('monto')
        batch_op.drop_column('monto_vigente')

    # ── shein_pedidos_articulos (NUEVA, detalle) ────────────────────────────
    op.create_table(
        'shein_pedidos_articulos',
        sa.Column('id_shein_articulo', sa.Integer(), nullable=False),
        sa.Column('id_shein_pedido', sa.Integer(), nullable=False),
        sa.Column('id_articulo', sa.String(length=20), nullable=True),
        sa.Column('producto', sa.String(length=60), nullable=False),
        sa.Column('tipo_producto', sa.Enum(
            'Nacional', 'Importado', name='tipoproductoshein'), nullable=False),
        sa.Column('monto', sa.Float(), nullable=False),
        sa.Column('monto_vigente', sa.Float(), nullable=True),
        sa.Column('estatus_articulo', sa.Enum(
            'vigente', 'confirmado', 'cancelado', name='estatusarticuloshein'), nullable=False),
        sa.ForeignKeyConstraint(['id_shein_pedido'], ['shein_pedidos.id_shein_pedido']),
        sa.PrimaryKeyConstraint('id_shein_articulo'),
    )
    op.create_index(
        op.f('ix_shein_pedidos_articulos_id_shein_articulo'),
        'shein_pedidos_articulos', ['id_shein_articulo'], unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f('ix_shein_pedidos_articulos_id_shein_articulo'),
        table_name='shein_pedidos_articulos',
    )
    op.drop_table('shein_pedidos_articulos')

    with op.batch_alter_table('shein_pedidos', recreate='always') as batch_op:
        batch_op.add_column(sa.Column('producto', sa.String(), nullable=False, server_default=''))
        batch_op.add_column(sa.Column('monto', sa.Float(), nullable=False, server_default='0'))
        batch_op.add_column(sa.Column('monto_vigente', sa.Float(), nullable=True))
        batch_op.drop_column('estatus_pago')
    with op.batch_alter_table('shein_pedidos', recreate='always') as batch_op:
        batch_op.alter_column('producto', server_default=None)
        batch_op.alter_column('monto', server_default=None)

    with op.batch_alter_table('shein_cortes', recreate='always') as batch_op:
        batch_op.add_column(sa.Column('porcentaje_bono', sa.Float(), nullable=False, server_default='0'))
        batch_op.alter_column('cupon', new_column_name='bono_monto')
        batch_op.alter_column('suma_pedidos', new_column_name='suma_montos')
        batch_op.drop_column('total_ticket')
    with op.batch_alter_table('shein_cortes', recreate='always') as batch_op:
        batch_op.alter_column('porcentaje_bono', server_default=None)

    op.drop_index(op.f('ix_precios_catalogo_id_precio'), table_name='precios_catalogo')
    op.drop_table('precios_catalogo')
