"""Add pinned flag to Post

Revision ID: 3a1b5c42e1a7
Revises: bbc69313308d
Create Date: 2025-11-21 12:45:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3a1b5c42e1a7'
down_revision = 'bbc69313308d'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('post', sa.Column('pinned', sa.Boolean(), nullable=False, server_default='0'))
    with op.batch_alter_table('post') as batch_op:
        batch_op.create_index(batch_op.f('ix_post_pinned'), ['pinned'], unique=False)


def downgrade():
    with op.batch_alter_table('post') as batch_op:
        batch_op.drop_index(batch_op.f('ix_post_pinned'))
    op.drop_column('post', 'pinned')