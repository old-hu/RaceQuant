# RaceQuant Development Guidelines

## 1. Project Goal

RaceQuant is a Hong Kong horse racing quantitative analysis system. The system should support historical data ingestion, feature engineering, probability modeling, odds comparison, backtesting, and disciplined betting decision support.

The system must prioritize:

- Reproducible data pipelines
- Probability-based model outputs
- Explainable race and horse analysis
- Backtestable strategy rules
- Clear separation between prediction and staking decisions

## 2. Technology Stack

### Backend

- Language: Python
- API framework: FastAPI
- Database ORM: SQLAlchemy
- Database: PostgreSQL
- Migration: Alembic
- Task queue: Celery or RQ
- Data analysis: pandas, numpy
- Machine learning: scikit-learn, LightGBM, XGBoost
- Testing: pytest

### Frontend

- Framework: React
- Build tool: Vite
- Language: TypeScript
- UI: shadcn/ui
- Styling: Tailwind CSS
- Charts: Recharts or ECharts
- API client: typed fetch client or TanStack Query

### Infrastructure

- Local orchestration: Docker Compose
- Backend package management: uv or Poetry
- Frontend package management: pnpm
- Environment configuration: `.env` and `.env.example`

## 3. Recommended Directory Structure

```text
RaceQuant/
├─ backend/
│  ├─ app/
│  │  ├─ api/
│  │  │  ├─ v1/
│  │  │  │  ├─ races.py
│  │  │  │  ├─ horses.py
│  │  │  │  ├─ odds.py
│  │  │  │  ├─ predictions.py
│  │  │  │  └─ backtests.py
│  │  ├─ core/
│  │  │  ├─ config.py
│  │  │  ├─ logging.py
│  │  │  └─ security.py
│  │  ├─ db/
│  │  │  ├─ session.py
│  │  │  ├─ models.py
│  │  │  └─ migrations/
│  │  ├─ schemas/
│  │  ├─ services/
│  │  │  ├─ data_ingestion.py
│  │  │  ├─ feature_engineering.py
│  │  │  ├─ prediction.py
│  │  │  ├─ odds_monitor.py
│  │  │  └─ staking.py
│  │  ├─ quant/
│  │  │  ├─ features/
│  │  │  │  ├─ horse.py
│  │  │  │  ├─ jockey.py
│  │  │  │  ├─ trainer.py
│  │  │  │  ├─ track.py
│  │  │  │  └─ odds.py
│  │  │  ├─ models/
│  │  │  │  ├─ win_prob.py
│  │  │  │  ├─ place_prob.py
│  │  │  │  └─ calibration.py
│  │  │  ├─ backtest/
│  │  │  │  ├─ engine.py
│  │  │  │  ├─ metrics.py
│  │  │  │  └─ strategies.py
│  │  │  └─ risk/
│  │  │     ├─ bankroll.py
│  │  │     └─ kelly.py
│  │  ├─ workers/
│  │  └─ main.py
│  ├─ tests/
│  ├─ pyproject.toml
│  └─ alembic.ini
│
├─ frontend/
│  ├─ src/
│  │  ├─ app/
│  │  ├─ components/
│  │  │  ├─ ui/
│  │  │  ├─ race-card/
│  │  │  ├─ odds-table/
│  │  │  ├─ prediction-board/
│  │  │  └─ backtest-chart/
│  │  ├─ features/
│  │  │  ├─ races/
│  │  │  ├─ horses/
│  │  │  ├─ predictions/
│  │  │  ├─ backtests/
│  │  │  └─ portfolio/
│  │  ├─ lib/
│  │  │  ├─ api.ts
│  │  │  ├─ utils.ts
│  │  │  └─ types.ts
│  │  ├─ hooks/
│  │  └─ styles/
│  ├─ package.json
│  ├─ tailwind.config.ts
│  └─ vite.config.ts
│
├─ data/
│  ├─ raw/
│  ├─ processed/
│  ├─ features/
│  └─ external/
│
├─ notebooks/
│  ├─ exploration/
│  ├─ feature_research/
│  └─ model_validation/
│
├─ models/
│  ├─ artifacts/
│  ├─ reports/
│  └─ experiments/
│
├─ scripts/
│  ├─ ingest_hkjc_data.py
│  ├─ build_features.py
│  ├─ train_model.py
│  └─ run_backtest.py
│
├─ docs/
│  ├─ development-guidelines.md
│  ├─ data_dictionary.md
│  ├─ betting_rules.md
│  ├─ model_methodology.md
│  └─ system_design.md
│
├─ docker/
│  ├─ backend.Dockerfile
│  └─ frontend.Dockerfile
│
├─ docker-compose.yml
├─ .env.example
├─ README.md
└─ Makefile
```

## 4. Quantitative Rules

### Probability First

All models must output probabilities. The system should not treat model output as a direct buy or no-buy signal.

Core outputs:

- Win probability
- Place probability
- Fair odds
- Edge versus market odds
- Confidence or uncertainty score

### Value Betting Rule

A betting candidate is valid only when model probability is greater than market implied probability plus a safety margin.

```text
model_probability > market_implied_probability + safety_margin
```

The safety margin should be configurable by bet type, race class, and liquidity conditions.

### Backtest Before Strategy Use

Every strategy must be backtested before it is shown as usable.

Minimum required metrics:

- ROI
- Hit rate
- Maximum drawdown
- Profit factor
- Average odds
- Bet count
- Bankroll curve

### Prediction and Staking Separation

Prediction modules estimate probability. Staking modules decide bet size. These concerns must remain separate in code and in the UI.

## 5. Hong Kong Racing Domain Priorities

Feature research should start with:

- Horse recent form
- Distance suitability
- Track and going suitability
- Draw bias
- Jockey and trainer statistics
- Class movement
- Weight carried
- Rest days
- Running style and pace map
- Official rating change
- Barrier trial signals
- Market odds movement

## 6. MVP Scope

The first version should include:

- Race list and race detail
- Horse profile and recent results
- Manual or file-based race data ingestion
- Basic odds import
- Win probability model
- Place probability model
- Prediction board
- Simple win/place backtest
- ROI, hit rate, drawdown, and bankroll chart

## 7. Development Rules

- Backend APIs should be versioned under `/api/v1`.
- Pydantic schemas should be used at API boundaries.
- Database models should not be returned directly from API routes.
- Feature generation should be deterministic and reproducible.
- Model artifacts should include metadata about training data, feature columns, and evaluation results.
- Frontend pages should consume typed API responses.
- shadcn/ui components should be kept under `frontend/src/components/ui`.
- Business logic should not live inside React components.
- Backtest assumptions must be documented before results are trusted.

