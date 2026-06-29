# Data Contract — DXC Airport Queue Management POC

> **FROZEN 2026-06-28.** Canonical internal schema. Every specialist references
> THIS file for table/column names and types. The data-engineer builds exactly
> these tables in DuckDB (`projects/dxc-poc/data/airport.duckdb`); the
> backend-engineer reads them; the test-engineer asserts them. If code and this
> file disagree, this file wins. Changes are append-only (see decision-log
> change history).

DuckDB types used: `VARCHAR`, `INTEGER`, `BIGINT`, `DOUBLE`, `DATE`,
`TIMESTAMP`, `BOOLEAN`. All timestamps are **naive local airport time** unless a
column name ends in `_utc`. All wait/duration values are in **minutes** unless
the name says otherwise.

---

## Enums (frozen)

### Airport codes (`airport_code VARCHAR`)
Exactly these five, uppercase IATA:

| Code | Airport | Lat | Lon |
|------|---------|-----|-----|
| `ATL` | Hartsfield-Jackson Atlanta | 33.6407 | -84.4277 |
| `DEN` | Denver International | 39.8561 | -104.6737 |
| `ORD` | Chicago O'Hare | 41.9742 | -87.9073 |
| `LAX` | Los Angeles International | 33.9416 | -118.4085 |
| `DFW` | Dallas/Fort Worth | 32.8998 | -97.0403 |

Lat/lon are frozen here so the UI map (`scatter_geo`) and the API `/airports`
response use identical coordinates. Stored in a small reference table
`airports_ref(airport_code, name, lat, lon)`.

### Queue area types (`area_type VARCHAR`)
Exactly these five:

| Value | Meaning |
|-------|---------|
| `SECURITY_TSA` | Standard TSA security checkpoint lane group |
| `SECURITY_PRECHECK` | TSA PreCheck expedited lane group |
| `CHECKIN` | Airline check-in / bag drop |
| `GATE` | Gate / boarding |
| `BAGGAGE` | Baggage claim / handling |

Real TSA data populates `SECURITY_TSA` and `SECURITY_PRECHECK`. Kaggle simulation
populates `CHECKIN`, `GATE`, `BAGGAGE`.

### Other small enums
- `sla_status VARCHAR` ∈ `OK | WARNING | BREACH`
- `severity VARCHAR` ∈ `LOW | MEDIUM | HIGH`
- `model_name VARCHAR` ∈ `prophet | nbeats | lstm` (forecast models, D4-A)
- `detector VARCHAR` ∈ `ecod | iforest | hst | stl | zscore` (D4-C)
- `anomaly_type VARCHAR` ∈ `SPIKE | DROP | CROSS_AIRPORT | SEASONAL`

---

## Table: `tsa_throughput` (REAL data + derived hourly)
Real TSA daily totals (one row per airport-date) **and** the deterministically
disaggregated checkpoint-hour rows. `grain` distinguishes them.

| Column | Type | Null? | Constraint / notes |
|--------|------|-------|--------------------|
| `airport_code` | VARCHAR | NOT NULL | ∈ airport enum |
| `obs_date` | DATE | NOT NULL | observation date |
| `obs_hour` | INTEGER | NULL | 0-23; NULL when `grain='daily'` |
| `area_type` | VARCHAR | NULL | ∈ {SECURITY_TSA, SECURITY_PRECHECK}; NULL when daily |
| `grain` | VARCHAR | NOT NULL | `daily` or `checkpoint_hour` |
| `pax` | INTEGER | NOT NULL | passengers screened in the period (≥ 0) |
| `lanes_open` | INTEGER | NULL | modelled open lanes for the hour (≥ 0) |
| `wait_min_est` | DOUBLE | NULL | derived M/M/c wait estimate (min, ≥ 0) |
| `mobility_index` | DOUBLE | NULL | ERAU Google-mobility regressor |
| `covid_cases` | INTEGER | NULL | ERAU regressor (national/regional) |
| `is_holiday` | BOOLEAN | NULL | US federal holiday flag |
| `source` | VARCHAR | NOT NULL | `mikelor` \| `erau` \| `derived` |

**Constraints/invariants (tested):**
- For each `(airport_code, obs_date)`, the sum of `pax` over all
  `grain='checkpoint_hour'` rows reconciles to the `grain='daily'` `pax`
  (± rounding from the disaggregation profile).
- `(airport_code, obs_date, obs_hour, area_type, grain)` is unique.

### Disaggregation profile constants (frozen — data-engineer implements verbatim)
Daily `pax` → checkpoint-hour `pax`:

- **Hourly weights** (fraction of daily pax by hour, 24 values summing to 1.0;
  bimodal): zero 00:00-03:00; ramp 04:00; AM peak 05:00-08:00 (~7% each);
  midday plateau 09:00-15:00 (~4% each); PM peak 16:00-19:00 (~6% each);
  taper 20:00-23:00. Exact vector lives in `data/profiles/hourly_weights.py`
  as `HOURLY_WEIGHTS: list[float]` (len 24, sum == 1.0 ± 1e-9).
- **Checkpoint split:** `SECURITY_TSA` = 0.80, `SECURITY_PRECHECK` = 0.20 of each
  airport's hourly pax (constant `CHECKPOINT_SPLIT`).
- Profile is **deterministic** (no RNG) so output is reproducible and testable.

### Wait-time derivation (M/M/c) constants (frozen)
For a checkpoint-hour: arrival rate `λ = pax / 60` (pax/min); per-lane service
rate `μ = SERVICE_RATE_PER_LANE` (default **3.0** pax/min/lane for SECURITY_TSA,
**6.0** for SECURITY_PRECHECK); servers `c = lanes_open`. `wait_min_est` =
M/M/c expected waiting time in queue (Wq), clamped to `[0, 120]`. `lanes_open`
defaults from a per-airport baseline lane table if not otherwise set. Formula
implemented in `backend/models/queue_math.py`, shared by ETL and SimPy.

---

## Table: `airport_ops` (SIMULATED — Kaggle)
Normalised long-format operations data for the non-TSA queue areas.

| Column | Type | Null? | Constraint / notes |
|--------|------|-------|--------------------|
| `airport_code` | VARCHAR | NOT NULL | ∈ airport enum (Kaggle hub mapped to one of the 5) |
| `area_type` | VARCHAR | NOT NULL | ∈ {CHECKIN, GATE, BAGGAGE} |
| `ts` | TIMESTAMP | NOT NULL | observation timestamp (local) |
| `queue_length` | INTEGER | NULL | passengers waiting (≥ 0) |
| `throughput` | INTEGER | NULL | passengers processed in the interval (≥ 0) |
| `wait_min` | DOUBLE | NULL | observed/simulated wait (min, ≥ 0) |
| `staff_on_duty` | INTEGER | NULL | staff count for the area-interval (≥ 0) |
| `resource_id` | VARCHAR | NULL | desk/belt/gate identifier from source |
| `source` | VARCHAR | NOT NULL | `kaggle` |

**Constraints/invariants:**
- `(airport_code, area_type, ts, resource_id)` unique.
- The Kaggle "major hub" is mapped deterministically across the 5 airports
  (documented in the ETL); `area_type` never contains TSA security values here.

---

## Table: `queue_predictions` (ML forecast output — D4-A)
One row per predicted minute-horizon point, per model.

| Column | Type | Null? | Constraint / notes |
|--------|------|-------|--------------------|
| `airport_code` | VARCHAR | NOT NULL | ∈ airport enum |
| `area_type` | VARCHAR | NOT NULL | ∈ area enum (usually SECURITY_TSA/PRECHECK) |
| `model_name` | VARCHAR | NOT NULL | ∈ model enum (prophet/nbeats/lstm) |
| `origin_ts` | TIMESTAMP | NOT NULL | the "now" the forecast was made from (the demo clock) |
| `horizon_min` | INTEGER | NOT NULL | minutes ahead of `origin_ts` (e.g. 15,30,45,60) |
| `target_ts` | TIMESTAMP | NOT NULL | `origin_ts + horizon_min` |
| `pred_wait_min` | DOUBLE | NOT NULL | predicted wait (min, ≥ 0) |
| `pred_throughput` | INTEGER | NULL | predicted pax for the period (≥ 0) |
| `lower_min` | DOUBLE | NULL | lower CI bound (min) |
| `upper_min` | DOUBLE | NULL | upper CI bound (min) |
| `generated_at` | TIMESTAMP | NOT NULL | when this row was written |

**Constraints/invariants:**
- `(airport_code, area_type, model_name, origin_ts, horizon_min)` unique.
- `target_ts == origin_ts + horizon_min` (tested).
- `pred_wait_min ≥ 0`; if both CI bounds present, `lower_min ≤ pred_wait_min ≤ upper_min`.

---

## Table: `anomaly_events` (D4-C)
One row per detected anomaly.

| Column | Type | Null? | Constraint / notes |
|--------|------|-------|--------------------|
| `event_id` | BIGINT | NOT NULL | surrogate id (monotonic) |
| `airport_code` | VARCHAR | NOT NULL | ∈ airport enum (or `ALL` for cross-airport) |
| `area_type` | VARCHAR | NULL | ∈ area enum; NULL for systemic |
| `detected_at` | TIMESTAMP | NOT NULL | when the anomaly occurred (demo-clock time) |
| `anomaly_type` | VARCHAR | NOT NULL | ∈ anomaly_type enum |
| `detector` | VARCHAR | NOT NULL | ∈ detector enum |
| `metric` | VARCHAR | NOT NULL | what was anomalous, e.g. `throughput`, `wait_min` |
| `observed_value` | DOUBLE | NOT NULL | the anomalous reading |
| `expected_value` | DOUBLE | NULL | model/baseline expectation |
| `score` | DOUBLE | NOT NULL | detector anomaly score (higher = more anomalous) |
| `severity` | VARCHAR | NOT NULL | ∈ severity enum |
| `description` | VARCHAR | NULL | human-readable summary for the UI |

**Constraints/invariants:**
- `event_id` unique. `severity` HIGH ⇒ surfaced as a Page-1 banner (D8).
- `airport_code == 'ALL'` only when `anomaly_type == 'CROSS_AIRPORT'`.

---

## Table: `staffing_recommendations` (D4-B output)
One row per airport-date-hour-checkpoint recommendation.

| Column | Type | Null? | Constraint / notes |
|--------|------|-------|--------------------|
| `airport_code` | VARCHAR | NOT NULL | ∈ airport enum |
| `rec_date` | DATE | NOT NULL | day the schedule applies to |
| `rec_hour` | INTEGER | NOT NULL | 0-23 |
| `area_type` | VARCHAR | NOT NULL | ∈ {SECURITY_TSA, SECURITY_PRECHECK} |
| `forecast_pax` | INTEGER | NOT NULL | demand the rec is sized for (≥ 0) |
| `recommended_lanes` | INTEGER | NOT NULL | lanes to open (≥ 0, ≤ physical cap) |
| `recommended_staff` | INTEGER | NOT NULL | officers (= lanes × officers-per-lane) |
| `expected_wait_min` | DOUBLE | NOT NULL | SimPy-validated expected wait (min) |
| `sla_target_min` | DOUBLE | NOT NULL | target used (default 10.0) |
| `sla_met` | BOOLEAN | NOT NULL | expected_wait_min ≤ sla_target_min |
| `generated_at` | TIMESTAMP | NOT NULL | when written |

**Constraints/invariants:**
- `(airport_code, rec_date, rec_hour, area_type)` unique.
- `recommended_lanes` ≤ per-airport-checkpoint physical cap (`LANE_CAPS` constant
  in `backend/config.py`, default cap 12 for SECURITY_TSA, 4 for SECURITY_PRECHECK).
- `recommended_staff == recommended_lanes * OFFICERS_PER_LANE` (default 2).

---

## Reference table: `airports_ref`
| Column | Type | Notes |
|--------|------|-------|
| `airport_code` | VARCHAR | PK, ∈ airport enum |
| `name` | VARCHAR | full airport name |
| `lat` | DOUBLE | from enum table above |
| `lon` | DOUBLE | from enum table above |
| `lane_cap_tsa` | INTEGER | physical SECURITY_TSA lane cap |
| `lane_cap_precheck` | INTEGER | physical SECURITY_PRECHECK lane cap |

Seeded from the frozen lat/lon values above.

---

## Shared constants (single source — `backend/config.py`)
The data-engineer and backend-engineer import these; do not duplicate literals.

| Constant | Default | Used by |
|----------|---------|---------|
| `SERVICE_RATE_PER_LANE` | {SECURITY_TSA: 3.0, SECURITY_PRECHECK: 6.0} pax/min | ETL wait calc, SimPy, staffing |
| `CHECKPOINT_SPLIT` | {SECURITY_TSA: 0.80, SECURITY_PRECHECK: 0.20} | disaggregation |
| `HOURLY_WEIGHTS` | 24-vector, sum 1.0 | disaggregation |
| `SLA_TARGET_MIN` | 10.0 | staffing, alerts |
| `WARN_WAIT_MIN` | 8.0 | alerts (sla_status) |
| `BREACH_WAIT_MIN` | 10.0 | alerts (sla_status) |
| `OFFICERS_PER_LANE` | 2 | staffing |
| `LANE_CAPS` | {SECURITY_TSA: 12, SECURITY_PRECHECK: 4} | staffing bound |
| `DEMO_NOW` | env `DEMO_NOW`, default a seeded surge date | current-state slice, clock |

---

## Build order & ownership
1. **data-engineer** creates all tables above + `airports_ref`, runs ETL
   (`tsa_throughput`, `airport_ops`), runs the disaggregation + wait derivation,
   then triggers model training which writes `queue_predictions`,
   `anomaly_events`, `staffing_recommendations`. DuckDB file is the handoff.
2. **backend-engineer** reads these tables read-only (never writes schema).
3. **ui-engineer** never touches DuckDB — only the API.
4. **test-engineer** asserts this contract (D10 #1, #2).
