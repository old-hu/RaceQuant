"""initial schema

Revision ID: 0001_initial_schema
Revises: None
Create Date: 2026-05-22

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "horses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("hkjc_id", sa.String(length=32), nullable=True),
        sa.Column("name_en", sa.String(length=128), nullable=True),
        sa.Column("name_zh", sa.String(length=128), nullable=True),
        sa.Column("country", sa.String(length=32), nullable=True),
        sa.Column("sex", sa.String(length=16), nullable=True),
        sa.Column("age", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("hkjc_id"),
    )
    op.create_table(
        "jockeys",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name_en", sa.String(length=128), nullable=True),
        sa.Column("name_zh", sa.String(length=128), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "races",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("race_date", sa.Date(), nullable=False),
        sa.Column("racecourse", sa.String(length=32), nullable=False),
        sa.Column("race_no", sa.Integer(), nullable=False),
        sa.Column("distance_m", sa.Integer(), nullable=True),
        sa.Column("surface", sa.String(length=32), nullable=True),
        sa.Column("going", sa.String(length=32), nullable=True),
        sa.Column("race_class", sa.String(length=32), nullable=True),
        sa.Column("name", sa.String(length=128), nullable=True),
        sa.Column("post_time", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("race_date", "racecourse", "race_no", name="uq_races_business_key"),
    )
    op.create_index(op.f("ix_races_race_date"), "races", ["race_date"], unique=False)
    op.create_index(op.f("ix_races_racecourse"), "races", ["racecourse"], unique=False)
    op.create_table(
        "trainers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name_en", sa.String(length=128), nullable=True),
        sa.Column("name_zh", sa.String(length=128), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "backtest_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("strategy_name", sa.String(length=64), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("parameters_json", sa.Text(), nullable=False),
        sa.Column("roi", sa.Numeric(precision=10, scale=6), nullable=True),
        sa.Column("hit_rate", sa.Numeric(precision=10, scale=6), nullable=True),
        sa.Column("max_drawdown", sa.Numeric(precision=10, scale=6), nullable=True),
        sa.Column("bet_count", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "runners",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("race_id", sa.Integer(), nullable=False),
        sa.Column("horse_id", sa.Integer(), nullable=True),
        sa.Column("jockey_id", sa.Integer(), nullable=True),
        sa.Column("trainer_id", sa.Integer(), nullable=True),
        sa.Column("horse_no", sa.Integer(), nullable=False),
        sa.Column("draw", sa.Integer(), nullable=True),
        sa.Column("carried_weight_lbs", sa.Integer(), nullable=True),
        sa.Column("declared_rating", sa.Integer(), nullable=True),
        sa.Column("gear", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.ForeignKeyConstraint(["horse_id"], ["horses.id"]),
        sa.ForeignKeyConstraint(["jockey_id"], ["jockeys.id"]),
        sa.ForeignKeyConstraint(["race_id"], ["races.id"]),
        sa.ForeignKeyConstraint(["trainer_id"], ["trainers.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("race_id", "horse_no", name="uq_runners_race_horse_no"),
    )
    op.create_index(op.f("ix_runners_horse_id"), "runners", ["horse_id"], unique=False)
    op.create_index(op.f("ix_runners_race_id"), "runners", ["race_id"], unique=False)
    op.create_table(
        "odds_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("race_id", sa.Integer(), nullable=False),
        sa.Column("runner_id", sa.Integer(), nullable=True),
        sa.Column("bet_type", sa.String(length=32), nullable=False),
        sa.Column("odds_value", sa.String(length=100), nullable=False),
        sa.Column("odds", sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column("implied_probability", sa.Numeric(precision=10, scale=6), nullable=True),
        sa.Column("pool_size", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("snapshot_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("legacy_id", sa.String(length=64), nullable=True),
        sa.Column("imported_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["race_id"], ["races.id"]),
        sa.ForeignKeyConstraint(["runner_id"], ["runners.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("race_id", "bet_type", "odds_value", "snapshot_at", "source", name="uq_odds_snapshot"),
    )
    op.create_index(op.f("ix_odds_snapshots_bet_type"), "odds_snapshots", ["bet_type"], unique=False)
    op.create_index(op.f("ix_odds_snapshots_legacy_id"), "odds_snapshots", ["legacy_id"], unique=False)
    op.create_index(op.f("ix_odds_snapshots_odds_value"), "odds_snapshots", ["odds_value"], unique=False)
    op.create_index(op.f("ix_odds_snapshots_race_id"), "odds_snapshots", ["race_id"], unique=False)
    op.create_index(op.f("ix_odds_snapshots_runner_id"), "odds_snapshots", ["runner_id"], unique=False)
    op.create_index(op.f("ix_odds_snapshots_snapshot_at"), "odds_snapshots", ["snapshot_at"], unique=False)
    op.create_table(
        "predictions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("race_id", sa.Integer(), nullable=False),
        sa.Column("runner_id", sa.Integer(), nullable=False),
        sa.Column("model_name", sa.String(length=64), nullable=False),
        sa.Column("model_version", sa.String(length=64), nullable=False),
        sa.Column("win_probability", sa.Numeric(precision=10, scale=6), nullable=True),
        sa.Column("place_probability", sa.Numeric(precision=10, scale=6), nullable=True),
        sa.Column("fair_win_odds", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("fair_place_odds", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["race_id"], ["races.id"]),
        sa.ForeignKeyConstraint(["runner_id"], ["runners.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_predictions_race_id"), "predictions", ["race_id"], unique=False)
    op.create_index(op.f("ix_predictions_runner_id"), "predictions", ["runner_id"], unique=False)
    op.create_table(
        "results",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("race_id", sa.Integer(), nullable=False),
        sa.Column("runner_id", sa.Integer(), nullable=False),
        sa.Column("finishing_position", sa.Integer(), nullable=True),
        sa.Column("beaten_margin", sa.String(length=32), nullable=True),
        sa.Column("win_dividend", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("place_dividend", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.ForeignKeyConstraint(["race_id"], ["races.id"]),
        sa.ForeignKeyConstraint(["runner_id"], ["runners.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("runner_id"),
    )
    op.create_index(op.f("ix_results_race_id"), "results", ["race_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_results_race_id"), table_name="results")
    op.drop_table("results")
    op.drop_index(op.f("ix_predictions_runner_id"), table_name="predictions")
    op.drop_index(op.f("ix_predictions_race_id"), table_name="predictions")
    op.drop_table("predictions")
    op.drop_index(op.f("ix_odds_snapshots_snapshot_at"), table_name="odds_snapshots")
    op.drop_index(op.f("ix_odds_snapshots_runner_id"), table_name="odds_snapshots")
    op.drop_index(op.f("ix_odds_snapshots_race_id"), table_name="odds_snapshots")
    op.drop_index(op.f("ix_odds_snapshots_odds_value"), table_name="odds_snapshots")
    op.drop_index(op.f("ix_odds_snapshots_legacy_id"), table_name="odds_snapshots")
    op.drop_index(op.f("ix_odds_snapshots_bet_type"), table_name="odds_snapshots")
    op.drop_table("odds_snapshots")
    op.drop_index(op.f("ix_runners_race_id"), table_name="runners")
    op.drop_index(op.f("ix_runners_horse_id"), table_name="runners")
    op.drop_table("runners")
    op.drop_table("backtest_runs")
    op.drop_table("trainers")
    op.drop_index(op.f("ix_races_racecourse"), table_name="races")
    op.drop_index(op.f("ix_races_race_date"), table_name="races")
    op.drop_table("races")
    op.drop_table("jockeys")
    op.drop_table("horses")
