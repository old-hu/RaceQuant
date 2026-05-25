# RaceQuant

RaceQuant is a Hong Kong horse-racing quantitative analysis system. Its current goal is to build a repeatable workflow for official historical race data, horse form history, model training, prediction review, value-betting research, and backtesting.

## Stack

- Backend: Python, FastAPI, SQLAlchemy, Alembic
- Frontend: React, Vite, TypeScript, Tailwind CSS, shadcn/ui-style components
- Research data: local SQLite under `data/processed`
- Raw cache: official HKJC scrape outputs under `data/raw/hkjc`
- Local orchestration: PowerShell scripts, Makefile, Docker Compose

## Repository Layout

```text
RaceQuant/
├── backend/      FastAPI app, DB models, quant services, tests
├── frontend/     React app and static JSON data views
├── data/         raw cache, processed SQLite DBs, reports, features
├── models/       trained model artifacts
├── scripts/      scraping, data build, audit, training, and local tools
├── docs/         project notes and data/modeling references
├── docker/       Dockerfiles
├── DESIGN.md
├── TASK_PLAN.md
├── README.md
└── Makefile
```

## Current Data Flow

1. `scripts/discover_official_race_days.py` scans HKJC official result dates and seeds real race-day jobs.
2. `scripts/run_historical_scrape_worker.py` backfills race cards, entries, results, dividends, changes, and missing horse-history pages.
3. `scripts/build_local_data.py --source raw` rebuilds local research SQLite data from raw HKJC cache.
4. `scripts/train_when_ready.py` waits until official scrape jobs are complete before rebuilding data, training the no-odds model, exporting predictions, and generating ranking reports.

The complete historical odds library is intentionally separate and remains a later data task.

## Local Development

Install frontend dependencies:

```powershell
cd frontend
npm install
cd ..
```

Start backend and frontend on Windows:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/start_local.ps1
```

Rebuild local data before starting:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/start_local.ps1 -RebuildData
```

Default URLs:

- Frontend: `http://127.0.0.1:5173/`
- Backend: `http://127.0.0.1:8000/`
- API docs: `http://127.0.0.1:8000/docs`

## Common Commands

```powershell
python scripts/build_local_data.py --source auto --reset
python scripts/train_when_ready.py --dry-run
python scripts/audit_structured_data.py
cd backend; python -m pytest; cd ..
cd frontend; npm run lint; npm run build; npm run smoke; cd ..
```

If GNU Make is installed:

```powershell
make quality
make train-when-ready
make docker-up
make docker-down
```

## Docker Compose

Docker Compose starts PostgreSQL, backend, and the built frontend preview:

```powershell
docker compose up --build
```

Stop services:

```powershell
docker compose down
```

The backend container mounts `data/` and `models/` so local scrape/cache/model artifacts remain outside the image.

## Key Documents

- `TASK_PLAN.md`: current execution plan and remaining work.
- `DESIGN.md`: frontend visual and UI standard.
- `docs/data_pipeline.md`: repeatable local data build and audit workflow.
- `docs/data_source_boundaries.md`: raw, SQLite, frontend cache, and formal DB boundaries.
- `docs/modeling_pipeline.md`: baseline model training flow and odds-mode rules.
- `docs/scraping_plan.md`: HKJC public-data scraping scope.
- `docs/betting_rules.md`: value betting and backtesting assumptions.
