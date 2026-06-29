# Swapping synthetic data for the real datasets

The ETL ships with **seeded synthetic generators** so `docker compose up` works
out of the box with zero credentials. The synthetic series deliberately matches
the *shape* of the real data (974 daily rows/airport, COVID trough + recovery,
holiday spikes, ERAU-style regressors). When you want real numbers, follow the
steps below. The DuckDB schema (`data-contract.md`) is unchanged either way —
you only replace the body of two generator functions.

> All real datasets here are CC BY 4.0 / Apache-2.0 / MIT / public domain, in
> line with the project licensing constraint (no GPL shipped).

---

## 1. TSA FOIA throughput — replaces `generate_tsa_data.run()`

### Option A — ERAU enriched dataset (recommended: regressors already joined)
- **Source:** https://datacommons.erau.edu/datasets/4dsy9vxxgx/1
  (Embry-Riddle, DOI 10.17632/4dsy9vxxgx.1, CC BY 4.0)
- **Why:** mobility + COVID features (`mobility_index`, `covid_cases`) are
  already joined per airport-date — a drop-in for the Prophet regressors.
- **Steps:**
  1. Download the CSV from the dataset landing page (no API key; manual download).
  2. Save it to `projects/dxc-poc/data/raw/erau_tsa.csv`.
  3. Commit a checksum:
     `shasum -a 256 data/raw/erau_tsa.csv > data/raw/erau_tsa.csv.sha256`
  4. In `generate_tsa_data.py`, replace the body of `run()` with a loader that
     reads `data/raw/erau_tsa.csv`, filters to the 5 airport codes, maps the
     source columns to the contract columns below, and inserts with
     `source='erau'`.

### Option B — mikelor processed CSVs (airport + checkpoint flows)
- **Source:** https://github.com/mikelor/TsaThroughput-Data (Apache-2.0)
- **Steps:**
  ```bash
  git clone https://github.com/mikelor/TsaThroughput-Data \
      projects/dxc-poc/data/raw/mikelor
  ```
  Then point the loader at the processed CSVs under that clone and insert with
  `source='mikelor'`. This source also carries hourly checkpoint detail, so you
  can bypass `disaggregate.py` for hours it covers (keep the disaggregation as a
  fallback for gaps).

### Option C — mikelor/TsaThroughput-Data raw repo (same project, PDF pipeline)
- Same clone as Option B; run the repo's PDF→JSON→CSV pipeline if you need the
  hour-level granularity rebuilt from source PDFs.

### Expected → contract column mapping (`tsa_throughput`, grain='daily')
| Contract column  | Real-source column (typical) |
|------------------|------------------------------|
| `airport_code`   | airport / IATA code (filter to ATL/DEN/ORD/LAX/DFW) |
| `obs_date`       | date                         |
| `pax`            | total daily throughput       |
| `mobility_index` | Google mobility metric (ERAU)|
| `covid_cases`    | national/regional case count (ERAU) |
| `is_holiday`     | derive via `pandas.tseries.holiday.USFederalHolidayCalendar` if absent |
| `source`         | `'erau'` or `'mikelor'`      |
| `obs_hour`/`area_type` | NULL for daily grain   |

After loading real daily rows, **`disaggregate.run()` and `train_models.run()`
work unchanged** — they read whatever is in `tsa_throughput`.

---

## 2. Kaggle Airport Operations — replaces `generate_ops_data.run()`

- **Source:** https://www.kaggle.com/datasets/sinanshereef/airport-operations-multi-table-dataset
- **Steps:**
  1. Install + auth the Kaggle CLI (needs a free Kaggle account + `~/.kaggle/kaggle.json`):
     ```bash
     pip install kaggle
     kaggle datasets download -d sinanshereef/airport-operations-multi-table-dataset \
         -p projects/dxc-poc/data/raw/kaggle --unzip
     ```
  2. Commit a checksum of the downloaded archive into `data/raw/`.
  3. In `generate_ops_data.py`, replace `run()` with a loader that reads the
     check-in / baggage / gate / workforce-shift tables, normalises them to the
     long format below, and **maps the single hub deterministically across the 5
     airports** (e.g. round-robin by table row index, documented in the ETL).

### Expected → contract column mapping (`airport_ops`)
| Contract column | Kaggle source (table → column) |
|-----------------|--------------------------------|
| `airport_code`  | assign by deterministic hub→5-airport mapping |
| `area_type`     | table identity → `CHECKIN` / `GATE` / `BAGGAGE` |
| `ts`            | event/observation timestamp    |
| `queue_length`  | queue / waiting count          |
| `throughput`    | passengers processed in interval |
| `wait_min`      | observed wait                  |
| `staff_on_duty` | workforce-shift headcount      |
| `resource_id`   | desk / belt / gate id          |
| `source`        | `'kaggle'`                     |

`area_type` must never contain TSA security values here (contract invariant).

---

## 3. mikelor/TsaThroughput-Data CSVs (quick raw clone)

If you only want the raw community CSVs without the ERAU enrichment:
```bash
git clone https://github.com/mikelor/TsaThroughput-Data \
    projects/dxc-poc/data/raw/mikelor
ls projects/dxc-poc/data/raw/mikelor   # inspect the processed CSV layout
```
Load the per-day per-airport CSVs into `tsa_throughput` with `source='mikelor'`,
then run `disaggregate.run()` for any hours not already at checkpoint grain.

---

## After swapping in real data

```bash
# from projects/dxc-poc/
rm -f data/airport.duckdb        # generators are idempotent; clear to force rebuild
python -m data.etl.run_etl       # rebuilds DuckDB from the real raw files
```

The data contract, API, UI, and tests are all unaffected — only the *origin* of
the rows changes, never their schema.
