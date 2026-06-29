# Demo Script -- DXC Airport Queue Management AI POC

> Walk-through for DXC stakeholders. Each step maps to a success criterion.
> Demo clock starts at **2021-11-24 07:00** (day before Thanksgiving -- peak surge).

---

## Setup

```bash
# Option A: Docker (one command)
docker compose up

# Option B: Local dev
python -m data.etl.run_etl          # builds the DuckDB (~30s)
uvicorn backend.app:app --port 8000 # API on :8000
cd ui && streamlit run Home.py      # Dashboard on :8501
```

Open **http://localhost:8501** in a browser.

---

## Step 1 -- Operations Command Center (Home)

**Success criterion:** Real data flowing through the system.

- Point to the **alert banners** at the top -- these are live anomaly detections (Thanksgiving pax spike at DFW, LAX, ORD).
- Show the **Actionable Recommendations** panel -- the system doesn't just detect problems, it tells you what to do: "Open 2 additional lanes at ATL SECURITY_TSA."
- Show the **US map** -- 5 airports colour-coded by SLA status. Hover for details.
- Show the **KPI gauges** -- worst wait, SLA compliance, anomalies, total pax.
- Show the **live queue table** -- every checkpoint, with wait time, lanes, trend arrows.
- Point out: "This is all powered by real TSA FOIA throughput data, 2020-2022."

---

## Step 2 -- Passenger Journey (Page 2)

**Success criterion:** End-to-end passenger experience visibility.

- Show the **Sankey diagram** -- passenger flow from Arrival through Check-in, Security, Immigration, Gate to Boarding. Width = volume, colour = health.
- Point to the **bottleneck callout** -- "Security (TSA) is the bottleneck at 120 min."
- Show the **journey summary** -- "A passenger arriving now will spend 10 min check-in, 120 min security, 16 min immigration, 7 min gate, 10 min baggage = 163 min total."
- Show the **stage detail cards** -- each stage colour-coded with queue depth and wait.
- Toggle **Compare all airports** -- grouped bar chart comparing journey times.

---

## Step 3 -- Queue Intelligence (Page 3)

**Success criterion:** Multi-area, multi-level queue visibility.

- Show **all 6 queue areas** for ATL -- Security TSA, PreCheck, Check-in, Immigration, Gate, Baggage. Each card shows wait, queue depth, staff count, SLA badge.
- Show the **heatmap** -- wait time by hour-of-day x day-of-week. "We can see the AM peak pattern every weekday at 06:00-08:00."
- Show the **area comparison** bar chart.

---

## Step 4 -- Predictive Intelligence (Page 4)

**Success criterion:** Next-hour wait-time forecast at each checkpoint.

- Show the **breach forecast callout** -- "SLA BREACH PREDICTED in 15 minutes."
- Show the **forecast chart** with confidence bands.
- Switch the **model selector** (Prophet, N-BEATS, LSTM) -- "We have 3 ML models running simultaneously."
- Toggle **multi-model comparison** -- all 3 models overlaid.
- Toggle **Compare all airports** -- see forecast across the network.

---

## Step 5 -- Anomaly Detection (Page 5)

**Success criterion:** Anomaly flagged when queue spikes.

- Show the **active incident cards** at the top -- HIGH-severity events with descriptions.
- Show the **anomaly timeline** scatter -- events over 24h, sized by score, coloured by severity.
- Show the **cross-airport analysis** -- "Are these anomalies local or systemic?"
- Point to the **type breakdown** -- SPIKE, DROP, SEASONAL, CROSS_AIRPORT.

---

## Step 6 -- Staffing Optimizer (Page 6)

- Select a date (2021-11-24) and click **Recommend**.
- Show the **schedule chart** -- recommended lanes per hour with shift boundaries.
- Point to the **cost estimate** -- total staff-hours x $35/hr.
- Show **SLA gap analysis** -- red-highlighted hours that fail SLA.

---

## Step 7 -- What-If Simulator (Page 7)

**Success criterion:** "What happens if I open an extra lane?"

- Set lanes from 4 to 8, click **Run Simulation**.
- Show the **before/after gauge charts** -- baseline vs scenario wait times.
- Show the **verdict** -- "Adding 4 lanes cuts mean wait by X min."
- Demonstrate **save scenario** -- compare up to 3 scenarios side by side.

---

## Step 8 -- Analytics & Reporting (Page 8)

**Success criterion:** All insights on a single dashboard.

- Show the **executive summary** -- auto-generated paragraph assessing the period.
- Show **KPI cards** with delta indicators (vs previous period).
- Show **trend charts** (tabs: wait time, pax volume, SLA breach rate).
- When airport = "All", show **airport ranking** -- who's best/worst.
- Click **Download Trend CSV** -- export for offline analysis.

---

## Closing

- Open **http://localhost:8000/docs** -- live interactive OpenAPI documentation.
- Emphasise: "Everything you've seen is powered by 3 ML model families, discrete-event simulation, and anomaly detection -- all running in real-time off a single DuckDB file."
- Stack: Python, FastAPI, Streamlit, Plotly, DuckDB, SimPy, PyOD, Prophet/Darts.
- All open-source, containerised, deployable anywhere.
