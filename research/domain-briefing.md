# Domain Briefing — Airport Queue Management AI POC (DXC)

> Written: 2026-06-28 | Status: COMPLETE — hand off to Solution Architect
> Output folder: `projects/dxc-poc/`

---

## 1. Executive Summary

Airport security and check-in queues are analytically rich, data-rich, and chronically
under-managed. Real hourly throughput data (TSA FOIA, 5 airports, 2020–2022) exists,
is freely available via GitHub, and is already in machine-readable form. A POC that
combines this real data with a simulated operations dataset, a suite of ML models
(forecasting, anomaly detection, staffing optimiser, scenario simulator), and a
multi-view dashboard will be technically impressive and immediately legible to a DXC
stakeholder. The domain is well-studied, open-source tooling is mature, and a working
demo can be built in one sprint.

**Feasibility verdict: HIGH.** Every component has a proven open-source implementation.
The risk is integration breadth, not technical depth.

---

## 2. Datasets — Verified Sources

### 2A. TSA FOIA Throughput — REAL DATA (PRIMARY, USE FIRST)

| Property | Detail |
|----------|--------|
| **Airports** | ATL, DEN, ORD, LAX, DFW (5 major US hubs) |
| **Date range** | 15 Feb 2020 – 15 Oct 2022 (974 daily observations per airport) |
| **Granularity** | Daily totals; TSA publishes hourly per-checkpoint in PDFs |
| **Key columns** | `pax` (daily throughput), mobility metrics (Google), COVID deaths/cases, search-trend signals |
| **License** | CC BY 4.0 |
| **Primary source** | https://datacommons.erau.edu/datasets/4dsy9vxxgx/1 (Embry-Riddle ERAU, DOI: 10.17632/4dsy9vxxgx.1) |
| **GitHub loader #1** | https://github.com/sullivankevint/TSA-througput-data — MIT license; airport + checkpoint level flows; Python + R cleaning scripts; quarterly files; last commit Jul 2020 (covers 2020 window) |
| **GitHub loader #2** | https://github.com/mikelor/TsaThroughput-Data — Apache-2.0; PDF→JSON→CSV pipeline; covers 2020–2022; three-year writeup at https://mikelor.github.io/three-years-of-tsathroughput |
| **GitHub scraper** | https://github.com/hunj/tsa-passenger-throughput — MIT; GitHub Actions auto-collector; chart.js visualisation |
| **Raw PDFs** | https://catalog.data.gov/dataset/tsa-foia-reading-room-weekly-passenger-throughput-data |
| **Integration effort** | LOW — CSV/JSON already processed; clone mikelor/TsaThroughput-Data and load directly |

**Recommended action:** Clone `mikelor/TsaThroughput-Data` for the processed CSVs + use
ERAU dataset for the enriched ML-ready version (mobility + COVID features already joined).

---

### 2B. Kaggle Airport Operations Multi-Table — SIMULATED DATA (SECONDARY)

| Property | Detail |
|----------|--------|
| **URL** | https://www.kaggle.com/datasets/sinanshereef/airport-operations-multi-table-dataset |
| **What it is** | End-to-end simulation of a major international airport hub |
| **Tables** | Flight schedules, passenger journeys, baggage handling, security processing, gate operations, workforce shifts, retail transactions, aircraft maintenance |
| **Value for POC** | Fills gaps TSA data doesn't cover: check-in queues, baggage, gate flows, staffing rosters |
| **Integration effort** | LOW — standard Kaggle download; CSV format |

**Download:** `kaggle datasets download -d sinanshereef/airport-operations-multi-table-dataset`

---

### 2C. BTS On-Time Performance Data (SUPPLEMENTARY)

| Property | Detail |
|----------|--------|
| **URL** | https://www.transtats.bts.gov/DL_SelectFields.aspx?gnoyr_VQ=FGJ |
| **What it covers** | Flight-level departure/arrival times, delays, cancellations |
| **Value** | Provides flight-schedule context for queue surge prediction (bunched arrivals → security surge) |
| **License** | Public domain (US government) |
| **Format** | CSV, monthly files |

---

### 2D. Data Gap Assessment

| Queue area | Real data available | Gap / mitigation |
|------------|--------------------|--------------------|
| Security (TSA) | YES — FOIA dataset | Use as primary |
| Check-in | NO | Simulate from Kaggle dataset |
| Immigration | NO | Simulate or stub |
| Baggage | NO | Kaggle simulation covers this |
| Gate / boarding | NO | BTS delays as proxy |

---

## 3. Open-Source Repositories — Assessed

### 3A. Data & Ingestion

| Repo | Stars | License | Fit | Notes |
|------|-------|---------|-----|-------|
| [mikelor/TsaThroughput](https://github.com/mikelor/TsaThroughput) | ~50 | Apache-2.0 | HIGH | PDF→JSON pipeline; actively maintained 2020–2022 |
| [sullivankevint/TSA-througput-data](https://github.com/sullivankevint/TSA-througput-data) | ~30 | MIT | HIGH | Airport + checkpoint level; Python/R scripts; 2020 window |
| [hunj/tsa-passenger-throughput](https://github.com/hunj/tsa-passenger-throughput) | ~20 | MIT | MEDIUM | Scraper + basic vis; good reference for auto-refresh |

### 3B. Simulation & Queue Modelling

| Repo | Language | License | Fit | Notes |
|------|----------|---------|-----|-------|
| [aschatz1995/Airport-Security-Wait-Sim](https://github.com/aschatz1995/Airport-Security-Wait-Sim) | Python/SimPy | — | HIGH | Simulates TSA checkpoint: ID check queues + baggage scanners; optimises lane count to stay under wait threshold |
| [rafaelm-soares/MOSIP-Airport-Passenger-Flow-Simulation](https://github.com/rafaelm-soares/MOSIP-Airport-Passenger-Flow-Simulation) | Java | — | MEDIUM | Full ticket-to-boarding discrete-event sim; queue lengths, delays, resource usage; good reference architecture |
| [hanelo/Interface-simulation](https://github.com/hanelo/Interface-simulation) | Python | — | MEDIUM | Queuing theory + Poisson distribution; stochastic passenger processing |
| [3amberloaf/Queue](https://github.com/3amberloaf/Queue) | Python | — | MEDIUM | 5-station queue simulation; models arrival, service, departure; wait-time and occupancy analysis |
| [adpoe/Airport-Simulation.py](https://github.com/adpoe/Airport-Simulation.py) | Python | — | MEDIUM | Discrete-event sim for small airport; staffing optimisation reference |

**Recommended:** Clone `aschatz1995/Airport-Security-Wait-Sim` as the "what-if lane simulator"
engine; use SimPy directly for any custom scenario modelling.

### 3C. ML / Forecasting

| Repo | Stars | License | Fit | Notes |
|------|-------|---------|-----|-------|
| [NASA/ML-airport-configuration](https://github.com/nasa/ML-airport-configuration) | ~200 | Apache-2.0 | MEDIUM | Kedro + MLflow pipeline for ML models; no checkpoint data but excellent MLOps pattern to copy |
| [NASA/ML-airport-data-services](https://github.com/nasa/ML-airport-data-services) | ~100 | Apache-2.0 | MEDIUM | Common ML-airport utilities; MLflow, scikit-learn, Kedro |
| [junzis/atdelay](https://github.com/junzis/atdelay) | ~300 | GPL-3.0 | LOW-MEDIUM | Flight delay prediction: RF, LSTM, DST-GAT; methodology transferable to queue forecasting |
| [LaurentBerder/Passengers_Prediction](https://github.com/LaurentBerder/Passengers_Prediction) | ~40 | — | HIGH | Time-series passenger count prediction; directly applicable |

**Recommended ML libraries (not repos — install as packages):**
- **Darts** (`pip install darts`) — best breadth: ARIMA, Prophet, LSTM, TFT, NBEATS in one API
- **Prophet** — strong for daily/weekly seasonality; handles COVID-era anomalies with regressors
- **NeuralForecast** (Nixtla) — LSTM, NHITS, TFT for deeper sequence modelling
- **PyOD** — 60+ anomaly detectors; tabular + time-series
- **River** — online/streaming anomaly detection for real-time lane monitoring

---

## 4. AI Use-Cases — Full Enumeration

### A. Queue Prediction & Wait-Time Forecasting

| Use-case | Best model(s) | Data needed | Complexity |
|----------|--------------|-------------|------------|
| A1. Short-term wait (next 15–60 min) | LSTM, NHITS, TFT | Hourly TSA throughput, lane count | Medium |
| A2. Day-of-week / time-of-day demand | Prophet, SARIMA | 2+ years of daily pax | Low |
| A3. Holiday & event surge prediction | Prophet + regressor, XGBoost | Flight schedule, public calendar | Medium |
| A4. COVID / exogenous shock impact | ARIMAX, Prophet + mobility regressors | ERAU enriched dataset | Low (data ready) |
| A5. Multi-airport comparative forecast | Multi-output LSTM, VAR | All 5 airports simultaneously | High |

**Published accuracy reference:** LSTM/RNN outperforms ARIMA on airport pax flow in
ScienceDirect study (DOI linked in sources). Prophet competitive for longer horizons.

---

### B. Staffing & Lane Optimisation

| Use-case | Best approach | Data needed | Complexity |
|----------|--------------|-------------|------------|
| B1. Optimal lane open/close schedule | Integer linear programming + demand forecast | Hourly forecast, staff cost | Medium |
| B2. Officer-per-lane allocation | Simulation (SimPy) + optimiser | Service-time distribution, throughput target | Medium |
| B3. PreCheck vs standard lane balance | Queuing theory (M/M/c model) + RL | PreCheck ratio, arrival rate | High |
| B4. Real-time lane recommendation | Rule engine on top of live forecast | Live sensor / camera feed | Low |

---

### C. Anomaly & Incident Detection

| Use-case | Best model(s) | Data needed | Complexity |
|----------|--------------|-------------|------------|
| C1. Queue spike detection (real-time) | River (online ARIMA), Isolation Forest | Rolling 15-min throughput | Low |
| C2. Throughput drop (equipment/incident) | PyOD ECOD, HBOS | Baseline throughput patterns | Low |
| C3. Cross-airport systemic anomaly | Multivariate Isolation Forest | All 5 airports in parallel | Medium |
| C4. Seasonal anomaly (day is weird) | STL decomposition + residual threshold | 2+ years history | Low |

---

### D. Passenger Flow & Routing

| Use-case | Best approach | Data needed | Complexity |
|----------|--------------|-------------|------------|
| D1. Dynamic re-routing to shorter queue | Real-time queue comparison + push alert | Live queue lengths, digital signage API | Medium |
| D2. Connecting passenger risk score | Remaining connection time vs queue forecast | Flight schedule + queue forecast | Medium |
| D3. Gate-to-security reverse flow risk | Time-to-gate calc + queue wait forecast | Gate distance, queue forecast | Medium |

---

### E. Capacity Planning & Scenario Modelling

| Use-case | Best approach | Data needed | Complexity |
|----------|--------------|-------------|------------|
| E1. Long-term demand forecast (1–5 yr) | Prophet + BTS trend, scenario trees | BTS historical + growth projections | Medium |
| E2. What-if: add a lane | SimPy simulation | Current arrival distribution, service time | Low |
| E3. What-if: change PreCheck ratio | M/M/c queuing model | PreCheck vs standard throughput rates | Low |
| E4. Infrastructure ROI modelling | Cost model on top of scenario sim | Staff cost, passenger value, SLA breach cost | Medium |

---

### F. Dashboard & Alerting

| Use-case | Tool | Data needed | Complexity |
|----------|------|-------------|------------|
| F1. Real-time ops dashboard | Streamlit (live) or Grafana | Live / simulated feed, queue predictions | Low |
| F2. Management KPI dashboard | Apache Superset or Streamlit | Historical + aggregated metrics | Low |
| F3. Predictive alert system | Custom alert engine + Streamlit | Threshold config + forecast | Low |
| F4. Historical benchmarking | Superset or Streamlit | All historical TSA data | Low |
| F5. Multi-airport map view | Plotly/Folium in Streamlit | Airport lat/long + KPIs | Low |

---

## 5. Recommended Tech Stack

### Decision: DuckDB + Python + Streamlit (for POC speed)

| Layer | Choice | Rationale |
|-------|--------|-----------|
| **Storage** | DuckDB | In-process, zero server, columnar analytics, reads Parquet/CSV directly; perfect for POC; upgrade path to TimescaleDB if real-time write throughput needed |
| **Data pipeline** | Python + Pandas + DuckDB | Simple ETL; no Airflow needed for POC scope |
| **ML / forecasting** | Darts + Prophet + PyOD | Single unified API across 20+ models; fastest path to multi-model comparison |
| **Simulation** | SimPy | Pure Python; Airport-Security-Wait-Sim is a working reference |
| **API** | FastAPI | Async, auto-OpenAPI docs, easy MLflow model serving |
| **Dashboard** | Streamlit | Fastest to real running UI; handles Python charts natively; integrates ML models directly |
| **Containerisation** | Docker Compose | API + Streamlit + DuckDB in one `docker-compose up` |

**Rejected options:**
- TimescaleDB: overkill for POC; add later if productionising
- Grafana: weak Python/ML integration; better for pure metrics monitoring
- Apache Superset: slow to set up; value only for SQL-analyst audience
- Airflow: no orchestration needed at POC scale

---

## 6. TSA / Airport Domain Vocabulary Primer

| Term | Meaning |
|------|---------|
| **Checkpoint** | Physical TSA security screening location within an airport terminal |
| **Lane** | Single screening line within a checkpoint (standard or PreCheck) |
| **TSA PreCheck** | Expedited screening programme; dedicated lanes; ~3× faster throughput |
| **Throughput** | Number of passengers screened per unit time (usually per hour or day) |
| **Wait time** | Queue entry to cleared-screening elapsed time |
| **WTMD** | Walk-Through Metal Detector — primary screening equipment |
| **AIT** | Advanced Imaging Technology (full-body scanner) — secondary option |
| **Divestiture** | Removing shoes, belts, electronics — the slow step before X-ray |
| **SSSS** | Secondary Security Screening Selection — triggers manual search |
| **Dwell time** | Total airport time including queue; relevant for retail revenue modelling |
| **M/M/c queue** | Markovian queuing model: Poisson arrivals, exponential service, c servers — standard queue theory baseline |
| **SLA** | Service Level Agreement — typically "95% of passengers cleared in <10 min" |
| **BTS** | Bureau of Transportation Statistics — flight schedule and delay data |
| **FOIA** | Freedom of Information Act — legal basis for TSA data release |

---

## 7. Open Questions for the Solution Architect

1. **Demo data mode:** Should the system auto-generate a realistic live feed (simulated real-time) to demo the real-time dashboard, or is batch replay of historical data sufficient?
2. **Checkpoint vs airport granularity:** TSA FOIA daily data is airport-level in the ERAU dataset; hourly checkpoint-level requires PDF extraction (mikelor pipeline). Which granularity does the demo need first?
3. **Staffing optimisation scope:** Full ILP solver (PuLP/OR-Tools) or a simpler heuristic rule engine for V1?
4. **Multi-airport map:** Include a Folium/Plotly map with all 5 airports as the dashboard hero view?
5. **Alert delivery:** In-dashboard alerts only, or also email/Slack for the demo?
6. **Docker vs local:** Single `docker-compose up` target, or assume local Python env for the demo?

---

## 8. Source List

- ERAU TSA Dataset: https://datacommons.erau.edu/datasets/4dsy9vxxgx/1
- TSA FOIA data.gov: https://catalog.data.gov/dataset/tsa-foia-reading-room-weekly-passenger-throughput-data
- mikelor/TsaThroughput-Data: https://github.com/mikelor/TsaThroughput-Data
- mikelor/TsaThroughput: https://github.com/mikelor/TsaThroughput
- sullivankevint/TSA-througput-data: https://github.com/sullivankevint/TSA-througput-data
- hunj/tsa-passenger-throughput: https://github.com/hunj/tsa-passenger-throughput
- Three Years of TSA Throughput (article): https://mikelor.github.io/three-years-of-tsathroughput
- Kaggle Airport Operations Multi-Table: https://www.kaggle.com/datasets/sinanshereef/airport-operations-multi-table-dataset
- BTS On-Time Data: https://www.transtats.bts.gov/
- aschatz1995/Airport-Security-Wait-Sim: https://github.com/aschatz1995/Airport-Security-Wait-Sim
- MOSIP Airport Simulation: https://github.com/rafaelm-soares/MOSIP-Airport-Passenger-Flow-Simulation
- 3amberloaf/Queue: https://github.com/3amberloaf/Queue
- adpoe/Airport-Simulation.py: https://github.com/adpoe/Airport-Simulation.py
- NASA ML-airport-configuration: https://github.com/nasa/ML-airport-configuration
- NASA ML-airport-data-services: https://github.com/nasa/ML-airport-data-services
- junzis/atdelay: https://github.com/junzis/atdelay
- ScienceDirect — LSTM vs ARIMA airport pax forecasting: https://www.sciencedirect.com/science/article/abs/pii/S0969699723001680
- PyOD: https://github.com/yzhao062/pyod
- Darts: https://unit8.com/resources/darts-time-series-made-easy-in-python/
- DuckDB vs TimescaleDB: https://www.influxdata.com/comparison/duckdb-vs-timescaledb/
- Streamlit vs Grafana: https://fastero.com/blog/streamlit-vs-grafana-when-to-use-each
