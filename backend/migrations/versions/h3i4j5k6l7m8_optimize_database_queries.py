"""Optimize database queries with additional indexes

Revision ID: h3i4j5k6l7m8
Revises: d4f83cc841e9
Create Date: 2025-10-28 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'h3i4j5k6l7m8'
down_revision = 'd4f83cc841e9'
branch_labels = None
depends_on = None


def upgrade():
    """
    Add database indexes for frequently queried columns to improve query performance.
    These indexes are based on common query patterns in the application.
    """
    
    # Indexes for documents table
    with op.batch_alter_table('documents', schema=None) as batch_op:
        # Index for filtering by owner_id (used in get_documents, document deletion)
        batch_op.create_index('ix_documents_owner_id', ['owner_id'], unique=False)
        # Composite index for owner_id + created_at (used in ordered queries)
        batch_op.create_index('ix_documents_owner_created', ['owner_id', 'created_at'], unique=False)
    
    # Indexes for requirements table
    with op.batch_alter_table('requirements', schema=None) as batch_op:
        # Index for filtering by owner_id (used in get_requirements, counts)
        batch_op.create_index('ix_requirements_owner_id', ['owner_id'], unique=False)
        # Index for filtering by source_document_id (used in document relationships)
        batch_op.create_index('ix_requirements_source_document_id', ['source_document_id'], unique=False)
        # Composite index for owner_id + status (used in filtered queries)
        batch_op.create_index('ix_requirements_owner_status', ['owner_id', 'status'], unique=False)
        # Index for req_id lookups (unique constraint already exists, but explicit index helps)
        # Note: unique constraint already creates an index, so we skip this
    
    # Indexes for project_summaries table
    with op.batch_alter_table('project_summaries', schema=None) as batch_op:
        # Composite index for owner_id + created_at (used in latest summary queries)
        batch_op.create_index('ix_project_summaries_owner_created', ['owner_id', 'created_at'], unique=False)
    
    # Indexes for user_profiles table
    with op.batch_alter_table('user_profiles', schema=None) as batch_op:
        # Index for user_id already exists (unique constraint)
        # Index for email lookups
        batch_op.create_index('ix_user_profiles_email', ['email'], unique=False)
    
    # Indexes for ambiguity_analyses table (additional to existing)
    with op.batch_alter_table('ambiguity_analyses', schema=None) as batch_op:
        # Index for requirement_id (used in requirement-specific queries)
        batch_op.create_index('ix_ambiguity_analyses_requirement_id', ['requirement_id'], unique=False)
        # Composite index for owner_id + analyzed_at (used in ordered queries)
        batch_op.create_index('ix_ambiguity_analyses_owner_analyzed', ['owner_id', 'analyzed_at'], unique=False)
        # Composite index for requirement_id + analyzed_at (used in latest analysis queries)
        batch_op.create_index('ix_ambiguity_analyses_req_analyzed', ['requirement_id', 'analyzed_at'], unique=False)
        # Index for status filtering
        batch_op.create_index('ix_ambiguity_analyses_status', ['status'], unique=False)
    
    # Indexes for clarification_history table (additional to existing)
    with op.batch_alter_table('clarification_history', schema=None) as batch_op:
        # Index for term_id (used in term clarification lookups)
        batch_op.create_index('ix_clarification_history_term_id', ['term_id'], unique=False)
        # Composite index for owner_id + clarified_at (used in history queries)
        batch_op.create_index('ix_clarification_history_owner_clarified', ['owner_id', 'clarified_at'], unique=False)
    
    # Indexes for tags table
    with op.batch_alter_table('tags', schema=None) as batch_op:
        # Index for name already exists (unique constraint)
        pass
    
    # Note: requirement_tags association table doesn't need additional indexes
    # as the primary key constraint on (requirement_id, tag_id) already creates indexes


def downgrade():
    """
    Remove the indexes added in upgrade.
    """
    
    # Remove indexes from documents table
    with op.batch_alter_table('documents', schema=None) as batch_op:
        batch_op.drop_index('ix_documents_owner_id')
        batch_op.drop_index('ix_documents_owner_created')
    
    # Remove indexes from requirements table
    with op.batch_alter_table('requirements', schema=None) as batch_op:
        batch_op.drop_index('ix_requirements_owner_id')
        batch_op.drop_index('ix_requirements_source_document_id')
        batch_op.drop_index('ix_requirements_owner_status')
    
    # Remove indexes from project_summaries table
    with op.batch_alter_table('project_summaries', schema=None) as batch_op:
        batch_op.drop_index('ix_project_summaries_owner_created')
    
    # Remove indexes from user_profiles table
    with op.batch_alter_table('user_profiles', schema=None) as batch_op:
        batch_op.drop_index('ix_user_profiles_email')
    
    # Remove indexes from ambiguity_analyses table
    with op.batch_alter_table('ambiguity_analyses', schema=None) as batch_op:
        batch_op.drop_index('ix_ambiguity_analyses_requirement_id')
        batch_op.drop_index('ix_ambiguity_analyses_owner_analyzed')
        batch_op.drop_index('ix_ambiguity_analyses_req_analyzed')
        batch_op.drop_index('ix_ambiguity_analyses_status')
    
    # Remove indexes from clarification_history table
    with op.batch_alter_table('clarification_history', schema=None) as batch_op:
        batch_op.drop_index('ix_clarification_history_term_id')
        batch_op.drop_index('ix_clarification_history_owner_clarified')
