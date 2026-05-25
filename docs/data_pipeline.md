# Data Pipeline

The repeatable local pipeline is:

1. Seed scrape jobs.
2. Run HKJC scrapers into `data/raw/hkjc`.
3. Parse raw cache into `data/processed/hkjc_structured.sqlite`.
4. Migrate or reuse historical odds in `data/processed/legacy_horse_odds.sqlite`.
5. Run structured and odds audits.
6. Write `data/reports/local_data_build.json`.
7. Build features, train models, generate predictions, and run backtests.
8. Export frontend JSON caches when a static UI cache is needed.

## Commands

Bootstrap from existing local data:

```powershell
python scripts/build_local_data.py --source auto --reset
```

Create raw cache for one race date first:

```powershell
python scripts/seed_historical_scrape_jobs.py --start-date 2026-05-20 --end-date 2026-05-20 --racecourses HV
python scripts/build_local_data.py --source raw --scrape-once
```

Run one pending scrape job directly:

```powershell
python scripts/run_historical_scrape_worker.py --once --db data/processed/hkjc_structured.sqlite --raw-dir data/raw/hkjc
```

Migrate full legacy odds when legacy MySQL credentials are available:

```powershell
$env:LEGACY_DB_PASSWORD="<password>"
python scripts/migrate_legacy_horse_odds.py --output data/processed/legacy_horse_odds.sqlite
```

Audit data:

```powershell
python scripts/audit_structured_data.py
python scripts/audit_legacy_odds.py
```

## Build Report

`scripts/build_local_data.py` writes `data/reports/local_data_build.json` with:

- source mode
- generated timestamp
- structured DB path
- odds DB path
- table counts
- date range
- structured data issue counts
- odds snapshot count
- odds duplicate and anomaly counts

