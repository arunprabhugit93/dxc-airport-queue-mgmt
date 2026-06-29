# DXC Airport Queue Management POC

## Context protocol (token-efficient)

### Starting a session
1. Read ONLY this file and `CHECKPOINT.md`
2. `CHECKPOINT.md` tells you the current state and what to work on
3. Do NOT read architecture/, research/, or contracts unless CHECKPOINT says to
4. Do NOT re-read files you already know about from the checkpoint

### During work
- Work on one piece at a time
- After completing each piece: update `CHECKPOINT.md` with what you did
- Do NOT accumulate context from prior pieces — the checkpoint is the memory

### Ending a session
- Update `CHECKPOINT.md` with final state
- Commit and push

### Context flush rule
After completing a self-contained task (e.g., "added endpoint X", "fixed page Y"),
**update CHECKPOINT.md immediately**. The next task starts fresh from the checkpoint,
not from accumulated conversation context. This prevents token waste from carrying
stale context forward.

---

## What this is
AI-powered airport queue management system for 5 US airports (ATL, DEN, ORD, LAX, DFW).
Covers 6 queue areas: Security TSA, PreCheck, Check-in, Immigration, Gate, Baggage.

## Stack
Python 3.12 | FastAPI (port 8000) | Streamlit (port 8501) | DuckDB | Plotly | SimPy

## To run
```bash
pip install -r requirements.txt
python -m data.etl.run_etl           # build DuckDB (~30s)
uvicorn backend.app:app --port 8000  # API
cd ui && streamlit run Home.py       # Dashboard
```

## Key rules
- Contracts in `architecture/` are law — code follows contracts
- `backend/config.py` is the single source of truth for constants
- All data is synthetic (seeded RNG, reproducible)
- DuckDB file is a build artifact, never committed
- No emojis in code. No comments unless the WHY is non-obvious.
- All widget keys in Streamlit must be unique (page-prefixed)
- Use `width="stretch"` not `use_container_width=True`

## Repo structure
```
backend/          FastAPI app + models + SimPy sim
  app.py          19 API endpoints
  config.py       shared constants (single source of truth)
  models/         queue math (M/M/c)
  sim/            SimPy checkpoint simulator
ui/               Streamlit dashboard (8 pages)
  api_client.py   API wrapper + shared helpers
  Home.py         Page 1: Operations Command Center
  pages/          Pages 2-8
data/             ETL pipeline + DuckDB
  etl/            5-step ETL (schema, TSA, disaggregate, ops, models)
tests/            pytest (16 tests)
architecture/     frozen contracts (data, API, UI spec)
docs/             demo script
```
