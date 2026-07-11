"""clientes: agrega dia_pago_especifico y frecuencia_pago_detalle

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-07-06

Ver docs/REGLAS_NEGOCIO.md §2 y docs/FULL_STACK/module_clientes.md (regla de
negocio frecuencia_pago, ajuste de fecha_pago_programada). Agrega 2 columnas
nullable a clientes, ya migrada en pos.db:

- dia_pago_especifico:     Integer, nullable. Obligatorio en el schema
                           (Pydantic) solo si frecuencia_pago = dia_especifico_mes.
- frecuencia_pago_detalle: String(60), nullable. Obligatorio en el schema
                           solo si frecuencia_pago = otro.

Ambas columnas son nullable a nivel de base de datos porque la obligatoriedad
es condicional (depende de frecuencia_pago) y SQLite/Alembic no expresan bien
un CHECK condicional entre columnas de forma portable — la validación
condicional vive en app/schemas/cliente.py (model_validator).

No requiere recreate='always' de la tabla: son columnas nuevas nullable sin
rename ni drop, soportadas de forma nativa por SQLite vía ADD COLUMN.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, Sequence[str], None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('clientes') as batch_op:
        batch_op.add_column(sa.Column('dia_pago_especifico', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('frecuencia_pago_detalle', sa.String(length=60), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('clientes') as batch_op:
        batch_op.drop_column('frecuencia_pago_detalle')
        batch_op.drop_column('dia_pago_especifico')
