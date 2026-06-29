# API Contract — DXC Airport Queue Management POC

> **FROZEN 2026-06-28.** FastAPI service in `projects/dxc-poc/backend/`,
> served by Uvicorn on **port 8000**, auto OpenAPI at `/docs`. The
> backend-engineer implements exactly these endpoints; the ui-engineer consumes
> exactly these shapes; the test-engineer asserts them (D10 #3). If code and this
> file disagree, this file wins. Changes are append-only.

## Conventions
- Base URL: `http://localhost:8000`. JSON in/out, UTF-8.
- All wait/duration fields are **minutes** (float). Timestamps are ISO-8601
  strings (`YYYY-MM-DDTHH:MM:SS`), naive local airport time.
- "Current" / "now" everywhere means the **demo clock** `DEMO_NOW`
  (see `/config/clock`), not wall-clock time.
- Errors: FastAPI default — `422` for validation, `404` for unknown airport,
  `400` for bad scenario params, `503` if models/DB not loaded. Error body:
  `{ "detail": <string|object> }`.
- Enums match `data-contract.md`: `airport_code`, `area_type`, `model_name`,
  `sla_status`, `severity`, `anomaly_type`.

---

## Endpoint index

| # | Method | Path | Top-5? |
|---|--------|------|--------|
| 1 | GET | `/health` | |
| 2 | GET | `/airports` | ✅ #2 |
| 3 | GET | `/queues/current` | ✅ #1 |
| 4 | GET | `/queues/forecast` | ✅ #3 |
| 5 | GET | `/anomalies/recent` | ✅ #4 |
| 6 | GET | `/staffing/recommend` | |
| 7 | POST | `/simulate/what-if` | ✅ #5 |
| 8 | GET | `/dashboard/kpis` | |
| 9 | GET | `/models` | |
| 10 | GET | `/config/clock` · POST `/config/clock` | |

---

## TOP-5 (full request/response shapes)

### #1 — `GET /queues/current`
Current queue state per airport/checkpoint at `DEMO_NOW`.

**Query params:** `airport` (optional, enum; omit = all 5 airports).

**200 response:**
```json
{
  "as_of": "2022-06-30T17:00:00",
  "queues": [
    {
      "airport_code": "ATL",
      "area_type": "SECURITY_TSA",
      "pax_last_hour": 4200,
      "lanes_open": 9,
      "wait_min": 11.4,
      "sla_status": "BREACH",
      "predicted_breach_in_min": 0,
      "trend": "UP"
    }
  ]
}
```
Field types: `as_of` str; `queues[]` objects with `airport_code` str(enum),
`area_type` str(enum), `pax_last_hour` int, `lanes_open` int, `wait_min` float,
`sla_status` str(enum), `predicted_breach_in_min` int|null, `trend` str ∈
`UP|DOWN|FLAT`.

---

### #2 — `GET /airports`
List of airports with current status (for map + selector).

**Query params:** none.

**200 response:**
```json
{
  "as_of": "2022-06-30T17:00:00",
  "airports": [
    {
      "airport_code": "ATL",
      "name": "Hartsfield-Jackson Atlanta",
      "lat": 33.6407,
      "lon": -84.4277,
      "worst_wait_min": 11.4,
      "sla_status": "BREACH",
      "active_anomalies": 1,
      "total_pax_today": 78000
    }
  ]
}
```
Types: `lat`/`lon` float; `worst_wait_min` float; `sla_status` str(enum);
`active_anomalies` int; `total_pax_today` int. `sla_status` is the worst across
that airport's checkpoints (drives map colour).

---

### #3 — `GET /queues/forecast`
Predicted wait times for the next N minutes.

**Query params:**
`airport` (required, enum) ·
`horizon` (optional int minutes, default 60, max 180) ·
`area` (optional, area enum, default `SECURITY_TSA`) ·
`model` (optional, model enum, default `prophet`).

**200 response:**
```json
{
  "airport_code": "ATL",
  "area_type": "SECURITY_TSA",
  "model_name": "prophet",
  "origin_ts": "2022-06-30T17:00:00",
  "horizon_min": 60,
  "points": [
    {
      "target_ts": "2022-06-30T17:15:00",
      "horizon_min": 15,
      "pred_wait_min": 10.2,
      "pred_throughput": 1050,
      "lower_min": 8.1,
      "upper_min": 12.6
    }
  ]
}
```
Types: `points[]` with `target_ts` str, `horizon_min` int, `pred_wait_min` float,
`pred_throughput` int|null, `lower_min`/`upper_min` float|null. Points ordered by
ascending `horizon_min`. Maps directly to `queue_predictions`.

---

### #4 — `GET /anomalies/recent`
Recent anomaly events.

**Query params:**
`airport` (optional, enum or `ALL`; omit = all) ·
`hours` (optional int, default 24, max 720).

**200 response:**
```json
{
  "as_of": "2022-06-30T17:00:00",
  "window_hours": 24,
  "events": [
    {
      "event_id": 412,
      "airport_code": "ATL",
      "area_type": "SECURITY_TSA",
      "detected_at": "2022-06-30T16:20:00",
      "anomaly_type": "SPIKE",
      "detector": "hst",
      "metric": "wait_min",
      "observed_value": 23.5,
      "expected_value": 9.0,
      "score": 0.92,
      "severity": "HIGH",
      "description": "Wait time spiked 2.6x above expected at ATL TSA."
    }
  ]
}
```
Types mirror `anomaly_events`. Ordered by `detected_at` descending.

---

### #5 — `POST /simulate/what-if`
Lane/staffing/PreCheck scenario simulation (SimPy, D7). Returns baseline vs
scenario.

**Request body:**
```json
{
  "airport_code": "ATL",
  "area_type": "SECURITY_TSA",
  "use_current_arrivals": true,
  "arrival_rate_per_min": null,
  "num_lanes": 6,
  "precheck_ratio": 0.2,
  "service_rate_per_lane": 3.0,
  "surge_multiplier": 1.0,
  "duration_min": 60
}
```
Rules: `num_lanes` 1-20, `duration_min` ≤ 240, `precheck_ratio` 0-1. If
`use_current_arrivals` true, `arrival_rate_per_min` is ignored and derived from
`DEMO_NOW` state. Out-of-range ⇒ `400`.

**200 response:**
```json
{
  "scenario": {
    "num_lanes": 6,
    "precheck_ratio": 0.2,
    "mean_wait_min": 6.8,
    "p95_wait_min": 12.1,
    "max_queue_len": 140,
    "lane_utilisation": 0.74,
    "sla_breach_min": 4,
    "sla_target_min": 10.0
  },
  "baseline": {
    "num_lanes": 4,
    "precheck_ratio": 0.2,
    "mean_wait_min": 14.9,
    "p95_wait_min": 28.0,
    "max_queue_len": 380,
    "lane_utilisation": 0.96,
    "sla_breach_min": 41,
    "sla_target_min": 10.0
  },
  "delta": {
    "mean_wait_min": -8.1,
    "sla_breach_min": -37
  }
}
```
`baseline` uses the airport/checkpoint's current open-lane count at `DEMO_NOW`.
All numeric fields float except counts (`num_lanes`, `max_queue_len`,
`sla_breach_min` are int).

---

## Remaining endpoints (shapes)

### `GET /health`
**200:**
```json
{ "status": "ok", "db_loaded": true, "models_loaded": ["prophet","nbeats","lstm"], "demo_now": "2022-06-30T17:00:00" }
```
`503` with `{"status":"degraded", ...}` if DB or models not loaded. Used by the
Docker healthcheck (D9) and `test-engineer`.

### `GET /staffing/recommend`
**Query:** `airport` (required, enum) · `date` (required, `YYYY-MM-DD`) ·
`area` (optional, default `SECURITY_TSA`) · `sla_target` (optional float, default 10.0).

**200:**
```json
{
  "airport_code": "ATL",
  "rec_date": "2022-06-30",
  "area_type": "SECURITY_TSA",
  "sla_target_min": 10.0,
  "hours": [
    {
      "rec_hour": 17,
      "forecast_pax": 4200,
      "recommended_lanes": 9,
      "recommended_staff": 18,
      "expected_wait_min": 8.7,
      "sla_met": true
    }
  ],
  "totals": { "peak_lanes": 11, "total_staff_hours": 230 }
}
```
Maps to `staffing_recommendations`. `hours[]` ordered by `rec_hour`.

### `GET /dashboard/kpis`
**Query:** `airport` (optional, enum or `ALL`, default `ALL`) ·
`date_from` (required, `YYYY-MM-DD`) · `date_to` (required, `YYYY-MM-DD`).

**200:**
```json
{
  "airport_code": "ALL",
  "date_from": "2022-01-01",
  "date_to": "2022-06-30",
  "kpis": {
    "avg_wait_min": 7.9,
    "p95_wait_min": 19.2,
    "total_pax": 14230000,
    "sla_breach_rate": 0.12,
    "anomaly_count": 38,
    "busiest_airport": "ATL",
    "busiest_hour": 17
  },
  "trend": [
    { "obs_date": "2022-01-01", "avg_wait_min": 6.2, "total_pax": 61000, "sla_breach_rate": 0.05 }
  ]
}
```
`trend[]` is one point per day in range (for the line charts). `sla_breach_rate`
is a 0-1 fraction.

### `GET /models`
**200:**
```json
{ "models": [
  { "name": "prophet", "label": "Prophet (seasonality + regressors)", "default": true,  "horizon_max_min": 180 },
  { "name": "nbeats",  "label": "N-BEATS (deep, short-horizon)",      "default": false, "horizon_max_min": 120 },
  { "name": "lstm",    "label": "LSTM (Darts RNN)",                   "default": false, "horizon_max_min": 120 }
] }
```
Feeds the Page-2 model selector.

### `GET /config/clock` · `POST /config/clock`
**GET 200:** `{ "demo_now": "2022-06-30T17:00:00", "min": "2020-02-15T00:00:00", "max": "2022-10-15T23:00:00" }`
**POST body:** `{ "demo_now": "2022-07-04T07:00:00" }` → **200** echoes the new
value. Lets the demo advance the clock to seeded surge/anomaly moments (D11). Out
of `[min,max]` ⇒ `400`.

---

## Endpoint → UI page → table map (for cross-checking)
| Endpoint | UI page (ui-spec) | Source table(s) |
|----------|-------------------|-----------------|
| `/airports`, `/queues/current` | Page 1 | tsa_throughput, airport_ops, anomaly_events |
| `/queues/forecast`, `/models` | Page 2 | queue_predictions |
| `/anomalies/recent` | Page 3 | anomaly_events |
| `/staffing/recommend` | Page 4 | staffing_recommendations |
| `/simulate/what-if` | Page 5 | (live SimPy; current state from tsa_throughput) |
| `/dashboard/kpis` | Page 6 | all (aggregated) |
| `/config/clock` | Page 1 sidebar | — |
| `/health` | (ops/test) | — |
