"""Fix req_id unique constraint to be per-user

Revision ID: i4j5k6l7m8n9
Revises: h3i4j5k6l7m8
Create Date: 2025-11-03 18:55:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'i4j5k6l7m8n9'
down_revision = 'h3i4j5k6l7m8'
branch_labels = None
depends_on = None


def upgrade():
    """
    Change req_id from globally unique to unique per owner_id.
    This allows different users to have requirements with the same req_id (e.g., REQ-001).
    """
    
    with op.batch_alter_table('requirements', schema=None) as batch_op:
        # Drop the existing unique constraint on req_id
        batch_op.drop_constraint('requirements_req_id_key', type_='unique')
        
        # Add a composite unique constraint on (req_id, owner_id)
        batch_op.create_unique_constraint(
            'uq_requirements_req_id_owner',
            ['req_id', 'owner_id']
        )


def downgrade():
    """
    Revert back to globally unique req_id.
    """
    
    with op.batch_alter_table('requirements', schema=None) as batch_op:
        # Drop the composite unique constraint
        batch_op.drop_constraint('uq_requirements_req_id_owner', type_='unique')
        
        # Restore the original unique constraint on req_id only
        batch_op.create_unique_constraint('requirements_req_id_key', ['req_id'])
