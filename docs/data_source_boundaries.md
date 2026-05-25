# Data Source Boundaries

RaceQuant uses three data layers. Keep their roles separate so research results can be reproduced.

## Raw Ingestion Layer

- Path: `data/raw/hkjc`
- Owner: scraper scripts under `scripts/scrape_*.py`
- Purpose: immutable local cache of HKJC pages and parsed table payloads.
- Rule: this layer is the preferred local rebuild source. Do not edit files here by hand except to remove a known bad scrape and re-run the scraper.

## Research SQLite Layer

- Structured DB: `data/processed/hkjc_structured.sqlite`
- Odds DB: `data/processed/legacy_horse_odds.sqlite`
- Owner: `scripts/build_local_data.py`, `scripts/hkjc_structured_store.py`, and odds migration scripts.
- Purpose: local development, feature generation, model training, backtesting, and API smoke runs.
- Rule: SQLite is disposable. It must be rebuildable from raw scrape cache, legacy odds migration, or explicit JSON cache bootstrap.

## Frontend JSON Cache

- Path: `frontend/public/data/*.json`
- Owner: export scripts such as `scripts/export_structured_data.py` and `scripts/export_odds_changes.py`
- Purpose: static UI cache and offline bootstrap only.
- Rule: frontend JSON is not a primary source of truth. Use `scripts/build_local_data.py --source json-cache` only when raw/local databases are unavailable.

## Formal Service Database

- Target: PostgreSQL through backend SQLAlchemy/Alembic models.
- Purpose: long-running service storage and future production deployment.
- Rule: PostgreSQL schema is the service contract; SQLite schema is the research/build cache. Field mapping is documented in `docs/schema_mapping.md`.

