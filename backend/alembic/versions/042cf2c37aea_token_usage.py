"""token_usage

Revision ID: 042cf2c37aea
Revises: 
Create Date: 2025-04-23 18:02:36.648972

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20250423_token_usage'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Añadir columna final_report a la tabla proposal_analysis_pipelines
    op.add_column('proposal_analysis_pipelines', sa.Column('final_report', postgresql.JSON(astext_type=sa.Text()), nullable=True))
    
    # Actualizar datos existentes si es necesario (opcional)
    # op.execute(
    #     """UPDATE proposal_analysis_pipelines 
    #        SET final_report = processing_metadata->>'final_report'
    #        WHERE processing_metadata->>'final_report' IS NOT NULL"""
    # )


def downgrade() -> None:
    # Eliminar la columna final_report de la tabla proposal_analysis_pipelines
    op.drop_column('proposal_analysis_pipelines', 'final_report')
