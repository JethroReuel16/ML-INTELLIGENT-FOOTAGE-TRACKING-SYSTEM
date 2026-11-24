"""Baseline schema: users, sessions, sources, searches, matches, evidence, multi-source.

Matches the schema that existed before migrations were introduced. For a
database created by hand earlier, run `alembic stamp 0001` once instead of
upgrading.

Revision ID: 0001
Revises:
Create Date: 2026-11-23
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import Text
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('users',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('full_name', sa.String(length=150), nullable=False),
    sa.Column('email', sa.String(length=255), nullable=False),
    sa.Column('hashed_password', sa.String(length=255), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_table('multi_source_searches',
    sa.Column('id', sa.String(length=100), nullable=False),
    sa.Column('owner_id', sa.Integer(), nullable=True),
    sa.Column('status', sa.String(length=50), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('source_count', sa.Integer(), nullable=True),
    sa.Column('successful_sources', sa.Integer(), nullable=True),
    sa.Column('failed_sources', sa.Integer(), nullable=True),
    sa.Column('settings', postgresql.JSONB(astext_type=Text()), nullable=True),
    sa.Column('matches_payload', postgresql.JSONB(astext_type=Text()), nullable=True),
    sa.Column('original_payload', postgresql.JSONB(astext_type=Text()), nullable=True),
    sa.Column('imported_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_multi_source_searches_id'), 'multi_source_searches', ['id'], unique=False)
    op.create_index(op.f('ix_multi_source_searches_owner_id'), 'multi_source_searches', ['owner_id'], unique=False)
    op.create_table('user_sessions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('token_hash', sa.String(length=64), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_sessions_id'), 'user_sessions', ['id'], unique=False)
    op.create_index(op.f('ix_user_sessions_token_hash'), 'user_sessions', ['token_hash'], unique=True)
    op.create_index(op.f('ix_user_sessions_user_id'), 'user_sessions', ['user_id'], unique=False)
    op.create_table('video_sources',
    sa.Column('id', sa.String(length=64), nullable=False),
    sa.Column('owner_id', sa.Integer(), nullable=True),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('source_type', sa.String(length=30), nullable=False),
    sa.Column('url', sa.Text(), nullable=False),
    sa.Column('location', sa.String(length=200), nullable=True),
    sa.Column('description', sa.String(length=500), nullable=True),
    sa.Column('last_connection_status', sa.String(length=50), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('last_tested_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_video_sources_id'), 'video_sources', ['id'], unique=False)
    op.create_index(op.f('ix_video_sources_owner_id'), 'video_sources', ['owner_id'], unique=False)
    op.create_table('searches',
    sa.Column('id', sa.String(length=100), nullable=False),
    sa.Column('owner_id', sa.Integer(), nullable=True),
    sa.Column('source_id', sa.String(length=64), nullable=True),
    sa.Column('status', sa.String(length=50), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('reference_data', postgresql.JSONB(astext_type=Text()), nullable=True),
    sa.Column('video_metadata', postgresql.JSONB(astext_type=Text()), nullable=True),
    sa.Column('search_settings', postgresql.JSONB(astext_type=Text()), nullable=True),
    sa.Column('video_path', sa.String(length=2048), nullable=True),
    sa.Column('reference_image_path', sa.String(length=2048), nullable=True),
    sa.Column('duration', sa.Float(), nullable=True),
    sa.Column('fps', sa.Float(), nullable=True),
    sa.Column('frame_count', sa.Integer(), nullable=True),
    sa.Column('result_payload', postgresql.JSONB(astext_type=Text()), nullable=True),
    sa.Column('summary_payload', postgresql.JSONB(astext_type=Text()), nullable=True),
    sa.Column('imported_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['source_id'], ['video_sources.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_searches_id'), 'searches', ['id'], unique=False)
    op.create_index(op.f('ix_searches_owner_id'), 'searches', ['owner_id'], unique=False)
    op.create_index(op.f('ix_searches_source_id'), 'searches', ['source_id'], unique=False)
    op.create_table('multi_source_items',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('multi_search_id', sa.String(length=100), nullable=False),
    sa.Column('source_id', sa.String(length=64), nullable=True),
    sa.Column('search_id', sa.String(length=100), nullable=True),
    sa.Column('source_name', sa.String(length=150), nullable=True),
    sa.Column('source_type', sa.String(length=30), nullable=True),
    sa.Column('status', sa.String(length=50), nullable=True),
    sa.Column('match_count', sa.Integer(), nullable=True),
    sa.Column('message', sa.String(length=1000), nullable=True),
    sa.Column('original_payload', postgresql.JSONB(astext_type=Text()), nullable=True),
    sa.ForeignKeyConstraint(['multi_search_id'], ['multi_source_searches.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['search_id'], ['searches.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['source_id'], ['video_sources.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_multi_source_items_id'), 'multi_source_items', ['id'], unique=False)
    op.create_index(op.f('ix_multi_source_items_multi_search_id'), 'multi_source_items', ['multi_search_id'], unique=False)
    op.create_table('search_matches',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('search_id', sa.String(length=100), nullable=False),
    sa.Column('rank', sa.Integer(), nullable=True),
    sa.Column('track_id', sa.Integer(), nullable=True),
    sa.Column('class_id', sa.Integer(), nullable=True),
    sa.Column('class_name', sa.String(length=150), nullable=True),
    sa.Column('match_status', sa.String(length=50), nullable=True),
    sa.Column('similarity_score', sa.Float(), nullable=True),
    sa.Column('ranking_score', sa.Float(), nullable=True),
    sa.Column('top3_average', sa.Float(), nullable=True),
    sa.Column('average_similarity', sa.Float(), nullable=True),
    sa.Column('timestamp', sa.Float(), nullable=True),
    sa.Column('frame_number', sa.Integer(), nullable=True),
    sa.Column('bbox', postgresql.JSONB(astext_type=Text()), nullable=True),
    sa.Column('detection_confidence', sa.Float(), nullable=True),
    sa.Column('frames_observed', sa.Integer(), nullable=True),
    sa.Column('evidence_image', sa.String(length=2048), nullable=True),
    sa.Column('original_payload', postgresql.JSONB(astext_type=Text()), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['search_id'], ['searches.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_search_matches_id'), 'search_matches', ['id'], unique=False)
    op.create_index(op.f('ix_search_matches_search_id'), 'search_matches', ['search_id'], unique=False)
    op.create_table('evidence_files',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('search_id', sa.String(length=100), nullable=False),
    sa.Column('match_id', sa.Integer(), nullable=True),
    sa.Column('file_path', sa.String(length=2048), nullable=False),
    sa.Column('file_type', sa.String(length=50), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['match_id'], ['search_matches.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['search_id'], ['searches.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_evidence_files_id'), 'evidence_files', ['id'], unique=False)
    op.create_index(op.f('ix_evidence_files_search_id'), 'evidence_files', ['search_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_evidence_files_id'), table_name='evidence_files')
    op.drop_index(op.f('ix_evidence_files_search_id'), table_name='evidence_files')
    op.drop_table('evidence_files')
    op.drop_index(op.f('ix_search_matches_id'), table_name='search_matches')
    op.drop_index(op.f('ix_search_matches_search_id'), table_name='search_matches')
    op.drop_table('search_matches')
    op.drop_index(op.f('ix_multi_source_items_id'), table_name='multi_source_items')
    op.drop_index(op.f('ix_multi_source_items_multi_search_id'), table_name='multi_source_items')
    op.drop_table('multi_source_items')
    op.drop_index(op.f('ix_searches_id'), table_name='searches')
    op.drop_index(op.f('ix_searches_owner_id'), table_name='searches')
    op.drop_index(op.f('ix_searches_source_id'), table_name='searches')
    op.drop_table('searches')
    op.drop_index(op.f('ix_video_sources_id'), table_name='video_sources')
    op.drop_index(op.f('ix_video_sources_owner_id'), table_name='video_sources')
    op.drop_table('video_sources')
    op.drop_index(op.f('ix_user_sessions_id'), table_name='user_sessions')
    op.drop_index(op.f('ix_user_sessions_token_hash'), table_name='user_sessions')
    op.drop_index(op.f('ix_user_sessions_user_id'), table_name='user_sessions')
    op.drop_table('user_sessions')
    op.drop_index(op.f('ix_multi_source_searches_id'), table_name='multi_source_searches')
    op.drop_index(op.f('ix_multi_source_searches_owner_id'), table_name='multi_source_searches')
    op.drop_table('multi_source_searches')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_table('users')
