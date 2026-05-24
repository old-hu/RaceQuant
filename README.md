# RaceQuant

RaceQuant is a Hong Kong horse racing quantitative analysis system.

The first product goal is to build a reproducible workflow for historical odds movement data, race data, probability modeling, value betting analysis, and backtesting.

## Tech Stack

- Backend: Python, FastAPI, SQLAlchemy, Alembic, PostgreSQL
- Frontend: React, Vite, TypeScript, Tailwind CSS, shadcn/ui
- Quant: pandas, numpy, scikit-learn, LightGBM or XGBoost
- Testing: pytest for backend, frontend smoke tests later
- Local orchestration: Docker Compose

## Repository Layout

```text
RaceQuant/
├─ backend/
├─ frontend/
├─ data/
├─ models/
├─ scripts/
├─ docs/
├─ docker/
├─ DESIGN.md
├─ TASK_PLAN.md
├─ README.md
├─ .env.example
└─ Makefile
```

## Current Execution Plan

See `TASK_PLAN.md`.

## Design Standard

All frontend UI work should follow `DESIGN.md`.

## Development Standard

Architecture and quant rules are documented in `docs/development-guidelines.md`.

## Project Documents

- `TASK_PLAN.md`: current execution plan.
- `DESIGN.md`: frontend visual and UI standard.
- `docs/data_quality_report.md`: structured data audit result and training-data readiness.
- `docs/modeling_pipeline.md`: baseline model training flow, odds-mode rules, metrics, and feature-query indexes.
- `docs/scraping_plan.md`: HKJC public-data scraping scope and scheduler modes.
- `docs/betting_rules.md`: value betting and backtesting assumptions.

## Local Development

Backend and frontend commands will be finalized as the skeleton is completed.

Initial intended commands:

```bash
make dev-backend
make dev-frontend
make test-backend
make lint-frontend
```

The frontend currently uses `corepack pnpm` because pnpm is available through Corepack on this machine.
