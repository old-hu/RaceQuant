# Schema Mapping

This document maps the current local research SQLite tables to the intended formal service schema.

## Race Core

| Research SQLite | Formal Service Target | Notes |
| --- | --- | --- |
| `race_metadata` | `races` | One row per race date, racecourse, race number. |
| `race_entries` | `race_entries` | One row per declared runner; includes standby flag. |
| `race_results` | `race_results` | One row per finished runner result. |
| `dividends` | `dividends` | One row per dividend pool and winning combination. |
| `race_change_events` | `race_change_events` | One row per race-day change event. |

## Horse History

| Research SQLite | Formal Service Target | Notes |
| --- | --- | --- |
| `horse_profiles` | `horses` | Current horse profile snapshot. |
| `horse_form_records` | `horse_form_records` | Historical form records keyed by horse and race index. |

## Odds

| Research SQLite | Formal Service Target | Notes |
| --- | --- | --- |
| `legacy_horse_odds` | `odds_snapshots` | Historical odds snapshots from legacy source. |

Required odds fields:

- `race_date`
- `race_no`
- `odds_type`
- `odds_value`
- `odds`
- `implied_probability`
- `snapshot_at`
- `source`

Expected odds types for the full historical library:

- `win`
- `fct`
- `qin`
- `qpl`

## Models And Backtests

| Research SQLite | Formal Service Target | Notes |
| --- | --- | --- |
| `model_predictions` | `model_predictions` | Stores probability payloads and model version. |
| `api_backtest_runs` | `backtest_runs` | Run-level config, assumptions, and metrics. |
| `api_backtest_bets` | `backtest_bets` | Executed bet records. |
| `api_backtest_candidate_explanations` | `backtest_candidate_explanations` | Selected and filtered candidate explanations. |
| `api_backtest_equity` | `backtest_equity_points` | Bankroll and drawdown curve. |

## Versioning Fields To Preserve

Every formal model/backtest record should preserve:

- data build report path or id
- training dataset version
- feature version
- model name and model version
- odds mode
- backtest config hash or version

