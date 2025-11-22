"""add pinned_by_user_id to post

Revision ID: f8fdd9e11ca5
Revises: eb5ceb9fc270
Create Date: 2025-11-21 16:58:33.617779

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f8fdd9e11ca5'
down_revision = 'eb5ceb9fc270'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('post', schema=None) as batch_op:
        batch_op.add_column(sa.Column('pinned_by_user_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_post_pinned_by_user_id_user', 'user', ['pinned_by_user_id'], ['id'])


def downgrade():
    with op.batch_alter_table('post', schema=None) as batch_op:
        batch_op.drop_constraint('fk_post_pinned_by_user_id_user', type_='foreignkey')
        batch_op.drop_column('pinned_by_user_id')
