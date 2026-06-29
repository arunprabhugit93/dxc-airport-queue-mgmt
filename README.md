# DXC Airport Queue Management AI POC

AI-powered airport queue management system covering 5 major US airports (ATL, DEN, ORD, LAX, DFW) with predictive forecasting, anomaly detection, staffing optimisation, and scenario simulation.

## Architecture

```
                    +----------------+
                    |   Streamlit    |  8 interactive pages
                    |   Dashboard    |  Plotly charts, Sankey diagrams,
                    |   (port 8501)  |  heatmaps, gauges
                    +-------+--------+
                            |
                    +-------v--------+
                    |    FastAPI     |  14 REST endpoints
                    |     API       |  Pydantic models, auto OpenAPI
                    |   (port 8000) |  SimPy simulation engine
                    +-------+--------+
                            |
                    +-------v--------+
                    |    DuckDB     |  6 tables, 4M+ rows
                    |   (in-proc)   |  Zero-server analytics
                    +-------+--------+
                            |
                    +-------v--------+
                    |   ETL + ML    |  Prophet, N-BEATS, LSTM
                    |   Pipeline    |  PyOD anomaly detection
                    +----------------+  M/M/c queueing math
```

## Quick start

### Docker (recommended)
```bash
docker compose up
# Dashboard: http://localhost:8501
# API docs:  http://localhost:8000/docs
```

### Local development
```bash
pip install -r requirements.txt
python -m data.etl.run_etl                    # build DuckDB (~30s)
uvicorn backend.app:app --port 8000 &         # start API
cd ui && streamlit run Home.py --server.port 8501  # start dashboard
```

## Dashboard pages

| # | Page | What it does |
|---|------|-------------|
| 1 | Operations Command Center | Live alerts, recommendations, map, KPI gauges, queue table |
| 2 | Passenger Journey | Sankey flow diagram, bottleneck identification, stage cards |
| 3 | Queue Intelligence | All 6 queue areas, heatmaps, area comparison |
| 4 | Predictive Intelligence | ML forecasts with CI bands, multi-model comparison |
| 5 | Anomaly Intelligence | Incident cards, timeline, cross-airport correlation |
| 6 | Staff & Lane Optimizer | Staffing schedule, shift boundaries, cost estimation |
| 7 | Scenario Simulator | What-if simulation, before/after gauges, scenario comparison |
| 8 | Analytics & Reporting | Executive summary, KPI trends, airport ranking |

## Queue areas covered

| Area | Data source | Description |
|------|------------|-------------|
| SECURITY_TSA | TSA FOIA (synthetic) | Standard TSA security checkpoint |
| SECURITY_PRECHECK | TSA FOIA (synthetic) | TSA PreCheck expedited lanes |
| CHECKIN | Simulated (Kaggle-style) | Airline check-in / bag drop |
| IMMIGRATION | Simulated | CBP customs & border control |
| GATE | Simulated | Gate / boarding area |
| BAGGAGE | Simulated | Baggage claim |

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Service health + model load status |
| GET | `/airports` | 5 airports with SLA status, coordinates |
| GET | `/queues/current` | Live security queue state |
| GET | `/queues/all-areas` | All 6 queue areas with wait/staff |
| GET | `/queues/forecast` | Predicted wait with CI bands |
| GET | `/queues/heatmap` | Hourly patterns for heatmap |
| GET | `/passenger-journey` | End-to-end passenger journey stages |
| GET | `/anomalies/recent` | Anomaly events with severity |
| GET | `/staffing/recommend` | Lane/staff schedule recommendations |
| POST | `/simulate/what-if` | SimPy scenario simulation |
| GET | `/operations/recommendations` | Actionable ops recommendations |
| GET | `/dashboard/kpis` | Historical KPIs with trends |
| GET | `/models` | Available forecast models |
| GET/POST | `/config/clock` | Demo clock control |

## ML models

- **Prophet** -- daily/weekly seasonality + COVID/holiday regressors
- **N-BEATS** (Darts) -- deep learning short-horizon forecast
- **LSTM** (Darts) -- recurrent neural network forecast
- **PyOD ECOD + IForest** -- batch anomaly detection
- **STL** -- seasonal decomposition anomaly detection
- **M/M/c queueing theory** -- wait-time derivation + staffing heuristic
- **SimPy** -- discrete-event simulation for what-if scenarios

## Demo clock

The system uses a virtual demo clock (`DEMO_NOW`) to replay historical data as if it were live. Default: `2021-11-24 07:00:00` (Thanksgiving surge). Adjust via the sidebar or `POST /config/clock`.

## Tech stack

Python 3.12 | FastAPI | Streamlit | Plotly | DuckDB | SimPy | Prophet | Darts | PyOD | Docker Compose

## License

All dependencies are MIT / Apache-2.0 / BSD. No GPL code shipped.
