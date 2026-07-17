"""renombra id_articulo a sku en shein_pedidos_articulos, String(20)->String(25), NOT NULL

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-07-17
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'f6a7b8c9d0e1'
down_revision = 'e5f6a7b8c9d0'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('shein_pedidos_articulos') as batch_op:
        batch_op.alter_column(
            'id_articulo',
            new_column_name='sku',
            existing_type=sa.String(length=20),
            type_=sa.String(length=25),
            existing_nullable=True,
            nullable=False,
        )


def downgrade():
    with op.batch_alter_table('shein_pedidos_articulos') as batch_op:
        batch_op.alter_column(
            'sku',
            new_column_name='id_articulo',
            existing_type=sa.String(length=25),
            type_=sa.String(length=20),
            existing_nullable=False,
            nullable=True,
        )
