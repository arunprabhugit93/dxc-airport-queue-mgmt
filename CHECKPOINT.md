# Checkpoint — current state

> Last updated: 2026-06-29

## Status: COMPLETE + Energy Management V1

### What exists
- **24 API endpoints** — all tested (19 pytest tests, all passing)
- **9 Next.js pages** — dark/light enterprise ops theme
- **6 queue areas** — SECURITY_TSA, SECURITY_PRECHECK, CHECKIN, IMMIGRATION, GATE, BAGGAGE
- **5 airports with terminals** — ATL, DEN, ORD, LAX, DFW
- **3 ML models** — Prophet, N-BEATS, LSTM (surrogate mode without darts/prophet installed)
- **DuckDB** — 4M+ rows, rebuilt from synthetic data in ~30s
- **Docker Compose** — 3 services (data, api, dashboard)
- **Docs** — README.md + docs/demo-script.md
- **Energy Management V1** — FastAPI endpoints + Next.js route with module-specific
  sidebar, backend scenario-case data, live temperature scenario lab,
  load forecast, demand response, tariff control, carbon/renewables, charging,
  asset health, comfort compliance, and recommendations

### API endpoints
Original (10): health, airports, queues/current, queues/forecast, anomalies/recent, staffing/recommend, simulate/what-if, dashboard/kpis, models, config/clock

Added in overhaul (5): queues/all-areas, passenger-journey, operations/recommendations, queues/heatmap, operations/shift-handoff

Added in v2 (4): airports/{code}/terminals, airports/{code}/capacity, airports/{code}/scorecard, network/health

Added in Energy Management V1 (6): energy/overview, energy/terminals, energy/temperature-profile, energy/scenario-cases, energy/setpoint-simulation, energy/recommendations

### Frontend routes
- Queue Management: `/`, `/journey`, `/queues`, `/forecast`, `/anomalies`, `/staffing`, `/simulator`, `/analytics`
- Energy Management: `/energy-management`

### What to work on next
- Docker build test (run `docker compose up` end to end)
- Install darts + prophet for real ML model training instead of surrogates
- Add real TSA FOIA data download (instructions in data/etl/download_real_data.md)
- Production hardening: logging, error monitoring, CORS config
- Energy Management V2: connect full CityLearn scenario runner or import a
  CityLearn-compatible airport terminal schema

### Files to read for specific tasks
- **Adding an endpoint**: read `backend/app.py` (patterns), `backend/config.py` (constants)
- **Adding a UI page**: read `ui/api_client.py` (API wrappers), any existing page for patterns
- **Changing data**: read `architecture/data-contract.md`, `data/etl/` modules
- **Changing API shapes**: read `architecture/api-contract.md`
- **Energy Management**: read `backend/app.py` energy models/endpoints,
  `frontend/src/app/energy-management/page.tsx`, `frontend/src/lib/api.ts`

---

## Safety protocol (prevents fix-one-break-another)

### After EVERY change, before committing:
1. **Run tests:** `python -m pytest tests/test_api.py -v` — all 16 must pass
2. **Start API + dashboard** and spot-check the affected page
3. If you changed a **shared file** (listed below), check ALL its consumers

### Shared files (high blast radius — changing these can break multiple things):
| File | Consumed by | If you change it, also check |
|------|------------|------------------------------|
| `backend/config.py` | ETL, backend, tests | Rebuild DB, rerun all tests, check UI |
| `backend/models/queue_math.py` | ETL disaggregation, staffing, SimPy | Rebuild DB, check staffing + what-if pages |
| `ui/api_client.py` | All 8 UI pages | Check every page loads |
| `architecture/data-contract.md` | ETL schema, backend queries, tests | Rebuild DB, rerun tests |
| `architecture/api-contract.md` | Backend endpoints, UI pages, tests | Check both backend + UI |

### Cross-layer dependency map:
```
config.py ──→ ETL (data generation)
         ──→ backend/app.py (all endpoints)
         ──→ queue_math.py (M/M/c formulas)
         ──→ tests

queue_math.py ──→ ETL disaggregation (wait derivation)
              ──→ staffing endpoint
              ──→ recommendations endpoint
              ──→ SimPy simulator

api_client.py ──→ Home.py, Journey, Queues, Forecast, Anomalies,
                  Staffing, WhatIf, Analytics (all pages)

DuckDB schema ──→ every backend query ──→ every UI page
```

### Rule: if tests pass, you're safe for backend changes.
### Rule: if tests pass AND the affected page loads, you're safe for UI changes.
### Rule: if you touch config.py or queue_math.py, rebuild the DB and run ALL tests.
