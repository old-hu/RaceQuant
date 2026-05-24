from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Race(Base):
    __tablename__ = "races"
    __table_args__ = (
        UniqueConstraint("race_date", "racecourse", "race_no", name="uq_races_business_key"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    race_date: Mapped[date] = mapped_column(Date, index=True)
    racecourse: Mapped[str] = mapped_column(String(32), index=True)
    race_no: Mapped[int] = mapped_column(Integer)
    distance_m: Mapped[int | None] = mapped_column(Integer, nullable=True)
    surface: Mapped[str | None] = mapped_column(String(32), nullable=True)
    going: Mapped[str | None] = mapped_column(String(32), nullable=True)
    race_class: Mapped[str | None] = mapped_column(String(32), nullable=True)
    name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    post_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    runners: Mapped[list["Runner"]] = relationship(back_populates="race")


class Horse(Base):
    __tablename__ = "horses"

    id: Mapped[int] = mapped_column(primary_key=True)
    hkjc_id: Mapped[str | None] = mapped_column(String(32), unique=True, nullable=True)
    name_en: Mapped[str | None] = mapped_column(String(128), nullable=True)
    name_zh: Mapped[str | None] = mapped_column(String(128), nullable=True)
    country: Mapped[str | None] = mapped_column(String(32), nullable=True)
    sex: Mapped[str | None] = mapped_column(String(16), nullable=True)
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)

    runners: Mapped[list["Runner"]] = relationship(back_populates="horse")


class Jockey(Base):
    __tablename__ = "jockeys"

    id: Mapped[int] = mapped_column(primary_key=True)
    name_en: Mapped[str | None] = mapped_column(String(128), nullable=True)
    name_zh: Mapped[str | None] = mapped_column(String(128), nullable=True)

    runners: Mapped[list["Runner"]] = relationship(back_populates="jockey")


class Trainer(Base):
    __tablename__ = "trainers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name_en: Mapped[str | None] = mapped_column(String(128), nullable=True)
    name_zh: Mapped[str | None] = mapped_column(String(128), nullable=True)

    runners: Mapped[list["Runner"]] = relationship(back_populates="trainer")


class Runner(Base):
    __tablename__ = "runners"
    __table_args__ = (
        UniqueConstraint("race_id", "horse_no", name="uq_runners_race_horse_no"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    race_id: Mapped[int] = mapped_column(ForeignKey("races.id"), index=True)
    horse_id: Mapped[int | None] = mapped_column(ForeignKey("horses.id"), nullable=True, index=True)
    jockey_id: Mapped[int | None] = mapped_column(ForeignKey("jockeys.id"), nullable=True)
    trainer_id: Mapped[int | None] = mapped_column(ForeignKey("trainers.id"), nullable=True)
    horse_no: Mapped[int] = mapped_column(Integer)
    draw: Mapped[int | None] = mapped_column(Integer, nullable=True)
    carried_weight_lbs: Mapped[int | None] = mapped_column(Integer, nullable=True)
    declared_rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    gear: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="declared")

    race: Mapped[Race] = relationship(back_populates="runners")
    horse: Mapped[Horse | None] = relationship(back_populates="runners")
    jockey: Mapped[Jockey | None] = relationship(back_populates="runners")
    trainer: Mapped[Trainer | None] = relationship(back_populates="runners")
    odds_snapshots: Mapped[list["OddsSnapshot"]] = relationship(back_populates="runner")
    result: Mapped["Result | None"] = relationship(back_populates="runner")


class OddsSnapshot(Base):
    __tablename__ = "odds_snapshots"
    __table_args__ = (
        UniqueConstraint("race_id", "bet_type", "odds_value", "snapshot_at", "source", name="uq_odds_snapshot"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    race_id: Mapped[int] = mapped_column(ForeignKey("races.id"), index=True)
    runner_id: Mapped[int | None] = mapped_column(ForeignKey("runners.id"), nullable=True, index=True)
    bet_type: Mapped[str] = mapped_column(String(32), index=True)
    odds_value: Mapped[str] = mapped_column(String(100), index=True)
    odds: Mapped[Decimal] = mapped_column(Numeric(10, 4))
    implied_probability: Mapped[Decimal | None] = mapped_column(Numeric(10, 6), nullable=True)
    pool_size: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    source: Mapped[str] = mapped_column(String(64), default="unknown")
    snapshot_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    legacy_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    runner: Mapped[Runner | None] = relationship(back_populates="odds_snapshots")


class Result(Base):
    __tablename__ = "results"

    id: Mapped[int] = mapped_column(primary_key=True)
    race_id: Mapped[int] = mapped_column(ForeignKey("races.id"), index=True)
    runner_id: Mapped[int] = mapped_column(ForeignKey("runners.id"), unique=True)
    finishing_position: Mapped[int | None] = mapped_column(Integer, nullable=True)
    beaten_margin: Mapped[str | None] = mapped_column(String(32), nullable=True)
    win_dividend: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    place_dividend: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)

    runner: Mapped[Runner] = relationship(back_populates="result")


class Prediction(Base):
    __tablename__ = "predictions"

    id: Mapped[int] = mapped_column(primary_key=True)
    race_id: Mapped[int] = mapped_column(ForeignKey("races.id"), index=True)
    runner_id: Mapped[int] = mapped_column(ForeignKey("runners.id"), index=True)
    model_name: Mapped[str] = mapped_column(String(64))
    model_version: Mapped[str] = mapped_column(String(64))
    win_probability: Mapped[Decimal | None] = mapped_column(Numeric(10, 6), nullable=True)
    place_probability: Mapped[Decimal | None] = mapped_column(Numeric(10, 6), nullable=True)
    fair_win_odds: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    fair_place_odds: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class BacktestRun(Base):
    __tablename__ = "backtest_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    strategy_name: Mapped[str] = mapped_column(String(64))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    parameters_json: Mapped[str] = mapped_column(Text)
    roi: Mapped[Decimal | None] = mapped_column(Numeric(10, 6), nullable=True)
    hit_rate: Mapped[Decimal | None] = mapped_column(Numeric(10, 6), nullable=True)
    max_drawdown: Mapped[Decimal | None] = mapped_column(Numeric(10, 6), nullable=True)
    bet_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
