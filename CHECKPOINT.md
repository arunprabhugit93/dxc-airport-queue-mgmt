# Checkpoint — current state

> Last updated: 2026-06-29

## Status: COMPLETE (POC ready for demo)

### What exists
- **19 API endpoints** — all tested (16 pytest tests, all passing)
- **8 Streamlit pages** — dark ops-dashboard theme, all error-free
- **6 queue areas** — SECURITY_TSA, SECURITY_PRECHECK, CHECKIN, IMMIGRATION, GATE, BAGGAGE
- **5 airports with terminals** — ATL, DEN, ORD, LAX, DFW
- **3 ML models** — Prophet, N-BEATS, LSTM (surrogate mode without darts/prophet installed)
- **DuckDB** — 4M+ rows, rebuilt from synthetic data in ~30s
- **Docker Compose** — 3 services (data, api, dashboard)
- **Docs** — README.md + docs/demo-script.md

### API endpoints
Original (10): health, airports, queues/current, queues/forecast, anomalies/recent, staffing/recommend, simulate/what-if, dashboard/kpis, models, config/clock

Added in overhaul (5): queues/all-areas, passenger-journey, operations/recommendations, queues/heatmap, operations/shift-handoff

Added in v2 (4): airports/{code}/terminals, airports/{code}/capacity, airports/{code}/scorecard, network/health

### What to work on next
- Docker build test (run `docker compose up` end to end)
- Install darts + prophet for real ML model training instead of surrogates
- Add real TSA FOIA data download (instructions in data/etl/download_real_data.md)
- Production hardening: logging, error monitoring, CORS config

### Files to read for specific tasks
- **Adding an endpoint**: read `backend/app.py` (patterns), `backend/config.py` (constants)
- **Adding a UI page**: read `ui/api_client.py` (API wrappers), any existing page for patterns
- **Changing data**: read `architecture/data-contract.md`, `data/etl/` modules
- **Changing API shapes**: read `architecture/api-contract.md`
