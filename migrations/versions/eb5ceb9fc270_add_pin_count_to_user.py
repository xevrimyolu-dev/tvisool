"""add pin_count to user

Revision ID: eb5ceb9fc270
Revises: 3a1b5c42e1a7
Create Date: 2025-11-21 16:31:52.811161

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'eb5ceb9fc270'
down_revision = '3a1b5c42e1a7'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(sa.Column('pin_count', sa.Integer(), nullable=False, server_default='0'))

    # ### end Alembic commands ###


def downgrade():
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_column('pin_count')

    # ### end Alembic commands ###
