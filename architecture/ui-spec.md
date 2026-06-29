# UI Wireframe Spec — DXC Airport Queue Management POC

> **FROZEN 2026-06-28.** Streamlit multipage app in `projects/dxc-poc/ui/`. The
> ui-engineer builds these six pages; each consumes **only** the API endpoints in
> `api-contract.md` (never DuckDB directly). Charts use **Plotly**. If code and
> this spec disagree, the contracts win. Changes are append-only.

## App-wide conventions
- Entry file `ui/Home.py` (renders Page 1); other pages in `ui/pages/` so
  Streamlit auto-builds the left nav in the order below.
- **Global sidebar (every page):** airport selector (ATL/DEN/ORD/LAX/DFW + "All"),
  and a **demo-clock control** (current `DEMO_NOW` display + "Advance"/date-time
  picker → `POST /config/clock`, then `st.rerun()`). API base URL from env
  `API_BASE` (default `http://localhost:8000`).
- API calls wrapped in `ui/api_client.py`; responses cached with
  `@st.cache_data(ttl=30)` keyed on params + `demo_now`.
- SLA colour map (reused everywhere): `OK`→green, `WARNING`→amber, `BREACH`→red.
  Severity map: `LOW`→grey, `MEDIUM`→amber, `HIGH`→red.
- A red banner appears at the top of **any** page when an active `HIGH`-severity
  anomaly exists for the selected airport (from `/anomalies/recent?hours=2`).

---

## Page 1 — Real-Time Operations Dashboard (`Home.py`)
**Title:** "Live Airport Operations".
**Sidebar controls:** global airport selector; demo-clock control; auto-refresh
toggle (re-pulls every 30s).

**Main panel (top→bottom):**
1. **Alert banner row** — red/amber banners for any `BREACH`/`HIGH` items at
   `DEMO_NOW` (from `/queues/current` `sla_status` + `/anomalies/recent`).
2. **Hero map** — Plotly `scatter_geo` of the 5 airports, marker colour = airport
   `sla_status`, marker size = `total_pax_today`, hover = name + worst_wait +
   active_anomalies. Source: `GET /airports`.
3. **KPI strip** — 4 `st.metric` cards: worst wait now, # checkpoints in BREACH,
   active anomalies, total pax today (aggregated from `/airports` +
   `/queues/current`).
4. **Live queue table** — one row per checkpoint for the selected airport
   (or all): area, lanes_open, wait_min, sla_status badge, trend arrow.
   Source: `GET /queues/current`.
5. **Next-60-min mini-forecast** — small Plotly line for the selected airport's
   SECURITY_TSA wait. Source: `GET /queues/forecast?horizon=60`.

**Data sources:** `/airports`, `/queues/current`, `/queues/forecast`,
`/anomalies/recent`, `/config/clock`.

---

## Page 2 — Forecast & Prediction (`pages/2_Forecast.py`)
**Title:** "Wait-Time Forecast".
**Sidebar controls:** airport selector; **model selector** (from `GET /models`);
checkpoint/area selector (SECURITY_TSA/PRECHECK); horizon slider (15-180 min,
capped by the model's `horizon_max_min`); "Compare all airports" toggle.

**Main panel:**
1. **Forecast chart** — Plotly line: `pred_wait_min` vs `target_ts`, with a shaded
   CI band (`lower_min`/`upper_min`). Horizontal SLA line at 10 min.
   Source: `GET /queues/forecast`.
2. **Multi-airport overlay** (when toggle on) — one line per airport on the same
   axes (loop `/queues/forecast` over the 5 codes).
3. **Throughput sub-chart** — `pred_throughput` vs `target_ts` (secondary chart).
4. **Forecast table + CSV download** — the raw `points[]`.

**Data sources:** `/models`, `/queues/forecast` (looped for multi-airport),
`/config/clock`.

---

## Page 3 — Anomaly Detection (`pages/3_Anomalies.py`)
**Title:** "Anomaly & Incident Detection".
**Sidebar controls:** airport selector (incl. "All" and `ALL`/systemic);
lookback window slider (1-720 h, default 24); anomaly-type multiselect
(SPIKE/DROP/CROSS_AIRPORT/SEASONAL); severity filter.

**Main panel:**
1. **Anomaly timeline** — Plotly scatter: x = `detected_at`, y = airport (or
   metric), marker colour = severity, size = `score`, hover = description.
   Source: `GET /anomalies/recent`.
2. **Type breakdown** — bar/pie of counts by `anomaly_type` and by `detector`.
3. **Cross-airport comparison** — grouped bar of anomaly counts per airport over
   the window (highlights systemic `ALL` events).
4. **Event detail table** — sortable: detected_at, airport, area, type, detector,
   observed vs expected, score, severity, description.

**Data sources:** `/anomalies/recent`, `/config/clock`.

---

## Page 4 — Staffing Optimiser (`pages/4_Staffing.py`)
**Title:** "Staffing & Lane Optimiser".
**Sidebar controls (inputs):** airport selector; **date picker** (within data
range); area selector (SECURITY_TSA/PRECHECK); **SLA-target slider** (5-20 min,
default 10); "Recommend" button.

**Main panel (outputs):**
1. **Recommended schedule chart** — Plotly bar: `recommended_lanes` per
   `rec_hour` (0-23), overlaid line of `forecast_pax`. SLA-met hours shaded green.
   Source: `GET /staffing/recommend`.
2. **Summary cards** — peak lanes, total staff-hours, hours meeting SLA
   (from `totals` + per-hour `sla_met`).
3. **Hourly schedule table** — rec_hour, forecast_pax, recommended_lanes,
   recommended_staff, expected_wait_min, sla_met. CSV download.

**Data sources:** `/staffing/recommend`, `/config/clock`.

---

## Page 5 — What-If Simulator (`pages/5_WhatIf.py`)
**Title:** "What-If Scenario Simulator".
**Sidebar controls (inputs):** airport selector; area selector; **lane-count
slider** (1-20); **PreCheck-ratio slider** (0-1, step 0.05); service-rate input
(default from area); **surge multiplier** slider (0.5-3.0); duration slider
(15-240 min); "Use current arrivals" toggle (else manual arrival-rate input);
"Run simulation" button.

**Main panel (outputs):**
1. **Baseline vs Scenario cards** — side-by-side `st.metric` with deltas:
   mean_wait, p95_wait, max_queue_len, lane_utilisation, sla_breach_min.
   Source: `POST /simulate/what-if`.
2. **Comparison bar chart** — Plotly grouped bars baseline vs scenario for the key
   metrics.
3. **Verdict callout** — green/red box: "Adding N lanes cuts mean wait by X min
   and clears the SLA breach" (from `delta`).

**Data sources:** `POST /simulate/what-if`, `/config/clock`.

---

## Page 6 — Historical Analytics & KPIs (`pages/6_Analytics.py`)
**Title:** "Historical Analytics & KPIs".
**Sidebar controls:** airport selector (incl. `ALL`); **date-range picker**
(`date_from`/`date_to`); metric toggle (wait / pax / SLA breach rate).

**Main panel:**
1. **KPI card row** — `st.metric` for avg_wait, p95_wait, total_pax,
   sla_breach_rate (as %), anomaly_count, busiest_airport/hour.
   Source: `GET /dashboard/kpis`.
2. **Trend charts** — Plotly lines over `trend[]`: avg_wait_min, total_pax,
   sla_breach_rate (one chart each or a multi-axis chart).
3. **Airport comparison** (when airport = `ALL`) — bar of avg_wait / total_pax per
   airport for the range.
4. **Download** — KPI summary + trend as CSV.

**Data sources:** `/dashboard/kpis`, `/config/clock`.

---

## Page → endpoint coverage (sanity check)
| Page | Primary endpoint(s) |
|------|---------------------|
| 1 Real-Time Ops | `/airports`, `/queues/current`, `/queues/forecast`, `/anomalies/recent` |
| 2 Forecast | `/models`, `/queues/forecast` |
| 3 Anomalies | `/anomalies/recent` |
| 4 Staffing | `/staffing/recommend` |
| 5 What-If | `POST /simulate/what-if` |
| 6 Analytics | `/dashboard/kpis` |
| (all) | `/config/clock`, `/health` |

Every endpoint in `api-contract.md` is consumed by at least one page, and every
page maps to the success criteria in the decision log (D11).
