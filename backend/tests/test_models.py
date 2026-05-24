from app.db.models import BacktestRun, Horse, Jockey, OddsSnapshot, Prediction, Race, Result, Runner, Trainer


def test_models_have_expected_table_names() -> None:
    assert Race.__tablename__ == "races"
    assert Runner.__tablename__ == "runners"
    assert Horse.__tablename__ == "horses"
    assert Jockey.__tablename__ == "jockeys"
    assert Trainer.__tablename__ == "trainers"
    assert OddsSnapshot.__tablename__ == "odds_snapshots"
    assert Result.__tablename__ == "results"
    assert Prediction.__tablename__ == "predictions"
    assert BacktestRun.__tablename__ == "backtest_runs"

