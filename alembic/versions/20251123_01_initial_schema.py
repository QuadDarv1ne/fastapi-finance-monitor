"""Initial schema based on SQLAlchemy models.

Revision ID: 20251123_01_initial_schema
Revises: None
Create Date: 2025-11-23
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20251123_01_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(), nullable=True, unique=True, index=True),
        sa.Column("email", sa.String(), nullable=True, unique=True, index=True),
        sa.Column("hashed_password", sa.String(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("1")),
        sa.Column("is_verified", sa.Boolean(), server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )

    op.create_table(
        "watchlists",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(), index=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )

    op.create_table(
        "watchlist_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("watchlist_id", sa.Integer(), sa.ForeignKey("watchlists.id")),
        sa.Column("symbol", sa.String(), index=True),
        sa.Column("name", sa.String()),
        sa.Column("asset_type", sa.String()),
        sa.Column("added_at", sa.DateTime(), nullable=True),
    )

    op.create_table(
        "portfolios",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(), index=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )

    op.create_table(
        "portfolio_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("portfolio_id", sa.Integer(), sa.ForeignKey("portfolios.id")),
        sa.Column("symbol", sa.String(), index=True),
        sa.Column("name", sa.String()),
        sa.Column("quantity", sa.Float()),
        sa.Column("purchase_price", sa.Float()),
        sa.Column("purchase_date", sa.DateTime()),
        sa.Column("asset_type", sa.String()),
    )

    op.create_table(
        "asset_historical_data",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("symbol", sa.String(), index=True),
        sa.Column("timestamp", sa.DateTime(), index=True),
        sa.Column("open_price", sa.Float()),
        sa.Column("high_price", sa.Float()),
        sa.Column("low_price", sa.Float()),
        sa.Column("close_price", sa.Float()),
        sa.Column("volume", sa.Integer()),
        sa.Column("asset_type", sa.String()),
    )

    op.create_table(
        "alerts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("symbol", sa.String(), index=True),
        sa.Column("alert_type", sa.String()),
        sa.Column("threshold", sa.Float()),
        sa.Column("extra_params", sa.Text()),
        sa.Column("notification_types", sa.Text()),
        sa.Column("schedule", sa.Text()),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("1")),
        sa.Column("description", sa.String()),
        sa.Column("created_at", sa.DateTime()),
        sa.Column("updated_at", sa.DateTime()),
    )

    op.create_table(
        "alert_trigger_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("alert_id", sa.Integer(), sa.ForeignKey("alerts.id")),
        sa.Column("triggered_at", sa.DateTime()),
        sa.Column("triggered_value", sa.Float()),
        sa.Column("condition_met", sa.Text()),
        sa.Column("notification_sent", sa.Boolean(), server_default=sa.text("0")),
    )

    op.create_table(
        "telegram_connections",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), unique=True, index=True),
        sa.Column("telegram_id", sa.String(), unique=True, index=True),
        sa.Column("telegram_username", sa.String(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("1")),
        sa.Column("connected_at", sa.DateTime(), nullable=True),
        sa.Column("last_notification_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("telegram_connections")
    op.drop_table("alert_trigger_history")
    op.drop_table("alerts")
    op.drop_table("asset_historical_data")
    op.drop_table("portfolio_items")
    op.drop_table("portfolios")
    op.drop_table("watchlist_items")
    op.drop_table("watchlists")
    op.drop_table("users")
