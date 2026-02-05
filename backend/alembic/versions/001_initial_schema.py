"""Initial database schema

Revision ID: 001_initial_schema
Revises:
Create Date: 2026-01-31

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum types
    op.execute("CREATE TYPE accounttype AS ENUM ('debito', 'credito', 'efectivo')")
    op.execute("CREATE TYPE categorytype AS ENUM ('ingreso', 'gasto', 'ambos')")
    op.execute("CREATE TYPE transactiontype AS ENUM ('ingreso', 'gasto')")

    # Create cuentas table
    op.create_table(
        'cuentas',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('nombre', sa.String(100), nullable=False),
        sa.Column('tipo', postgresql.ENUM('debito', 'credito', 'efectivo', name='accounttype'), nullable=False),
        sa.Column('divisa', sa.String(3), nullable=False),
        sa.Column('descripcion', sa.String(500), nullable=True),
        sa.Column('tags', postgresql.ARRAY(sa.String(50)), nullable=False, server_default='{}'),
        sa.Column('activa', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
    )
    op.create_index('idx_cuentas_activa', 'cuentas', ['activa'])
    op.create_index('idx_cuentas_divisa', 'cuentas', ['divisa'])

    # Create categorias table
    op.create_table(
        'categorias',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('nombre', sa.String(50), nullable=False),
        sa.Column('tipo', postgresql.ENUM('ingreso', 'gasto', 'ambos', name='categorytype'), nullable=False),
        sa.Column('icono', sa.String(50), nullable=True),
        sa.Column('color', sa.String(7), nullable=True),
        sa.Column('categoria_padre_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('categorias.id'), nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
    )
    op.create_index('idx_categorias_tipo', 'categorias', ['tipo'])
    op.create_index('idx_categorias_padre', 'categorias', ['categoria_padre_id'])

    # Create transacciones table
    op.create_table(
        'transacciones',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tipo', postgresql.ENUM('ingreso', 'gasto', name='transactiontype'), nullable=False),
        sa.Column('monto', sa.Numeric(15, 2), nullable=False),
        sa.Column('fecha', sa.Date, nullable=False),
        sa.Column('cuenta_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('cuentas.id'), nullable=False),
        sa.Column('categoria_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('categorias.id'), nullable=False),
        sa.Column('titulo', sa.String(100), nullable=True),
        sa.Column('descripcion', sa.String(500), nullable=True),
        sa.Column('tags', postgresql.ARRAY(sa.String(50)), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
    )
    op.create_index('idx_transacciones_cuenta_fecha', 'transacciones', ['cuenta_id', 'fecha'])
    op.create_index('idx_transacciones_cuenta_tipo', 'transacciones', ['cuenta_id', 'tipo'])
    op.create_index('idx_transacciones_categoria', 'transacciones', ['categoria_id'])
    op.create_index('idx_transacciones_fecha', 'transacciones', ['fecha'])

    # Create transferencias table
    op.create_table(
        'transferencias',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('cuenta_origen_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('cuentas.id'), nullable=False),
        sa.Column('cuenta_destino_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('cuentas.id'), nullable=False),
        sa.Column('monto', sa.Numeric(15, 2), nullable=False),
        sa.Column('fecha', sa.Date, nullable=False),
        sa.Column('descripcion', sa.String(500), nullable=True),
        sa.Column('tags', postgresql.ARRAY(sa.String(50)), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
    )
    op.create_index('idx_transferencias_origen', 'transferencias', ['cuenta_origen_id'])
    op.create_index('idx_transferencias_destino', 'transferencias', ['cuenta_destino_id'])
    op.create_index('idx_transferencias_fecha', 'transferencias', ['fecha'])


def downgrade() -> None:
    # Drop tables
    op.drop_table('transferencias')
    op.drop_table('transacciones')
    op.drop_table('categorias')
    op.drop_table('cuentas')

    # Drop enum types
    op.execute('DROP TYPE transactiontype')
    op.execute('DROP TYPE categorytype')
    op.execute('DROP TYPE accounttype')
