from __future__ import annotations

import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore", message="Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.")

from starlette.testclient import TestClient

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from backend.app import app


def _client() -> TestClient:
    return TestClient(app)


def test_health_reports_ready_state() -> None:
    with _client() as client:
        response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["db_loaded"] is True
    assert payload["models_loaded"] == ["prophet", "nbeats", "lstm"]


def test_queue_endpoints_cover_both_security_areas() -> None:
    with _client() as client:
        current = client.get("/queues/current")
        tsa_forecast = client.get("/queues/forecast", params={"airport": "ATL"})
        precheck_forecast = client.get(
            "/queues/forecast",
            params={"airport": "ATL", "area": "SECURITY_PRECHECK"},
        )

    assert current.status_code == 200
    queues = current.json()["queues"]
    assert any(item["area_type"] == "SECURITY_TSA" for item in queues)
    assert any(item["area_type"] == "SECURITY_PRECHECK" for item in queues)

    assert tsa_forecast.status_code == 200
    assert tsa_forecast.json()["points"]

    assert precheck_forecast.status_code == 200
    assert precheck_forecast.json()["points"]


def test_clock_update_round_trip() -> None:
    with _client() as client:
        before = client.get("/config/clock")
        assert before.status_code == 200
        original_demo_now = before.json()["demo_now"]

        updated = client.post("/config/clock", json={"demo_now": "2022-07-04T07:00:00"})
        restored = client.post("/config/clock", json={"demo_now": original_demo_now})

    assert updated.status_code == 200
    assert updated.json()["demo_now"] == "2022-07-04T07:00:00"
    assert restored.status_code == 200
    assert restored.json()["demo_now"] == original_demo_now


def test_staffing_simulation_and_kpis() -> None:
    with _client() as client:
        staffing = client.get(
            "/staffing/recommend",
            params={"airport": "ATL", "date": "2021-11-24"},
        )
        simulation = client.post(
            "/simulate/what-if",
            json={
                "airport_code": "ATL",
                "area_type": "SECURITY_TSA",
                "use_current_arrivals": True,
                "arrival_rate_per_min": None,
                "num_lanes": 6,
                "precheck_ratio": 0.2,
                "service_rate_per_lane": 3.0,
                "surge_multiplier": 1.0,
                "duration_min": 60,
            },
        )
        kpis = client.get(
            "/dashboard/kpis",
            params={"date_from": "2021-11-20", "date_to": "2021-11-24"},
        )

    assert staffing.status_code == 200
    staffing_payload = staffing.json()
    assert staffing_payload["hours"]
    assert staffing_payload["totals"]["peak_lanes"] >= 0

    assert simulation.status_code == 200
    simulation_payload = simulation.json()
    assert simulation_payload["baseline"]["num_lanes"] > 0
    assert simulation_payload["scenario"]["num_lanes"] == 6

    assert kpis.status_code == 200
    kpi_payload = kpis.json()
    assert kpi_payload["trend"]
    assert kpi_payload["kpis"]["total_pax"] > 0


def test_passenger_journey_returns_all_stages() -> None:
    with _client() as client:
        response = client.get("/passenger-journey", params={"airport": "ATL"})

    assert response.status_code == 200
    data = response.json()
    assert data["airport_code"] == "ATL"
    stages = data["stages"]
    stage_names = [s["stage"] for s in stages]
    assert "CHECKIN" in stage_names
    assert "SECURITY_TSA" in stage_names
    assert "IMMIGRATION" in stage_names
    assert "GATE" in stage_names
    assert data["total_journey_min"] > 0
    assert data["bottleneck"] in stage_names


def test_all_areas_returns_security_and_ops() -> None:
    with _client() as client:
        response = client.get("/queues/all-areas", params={"airport": "ATL"})

    assert response.status_code == 200
    queues = response.json()["queues"]
    area_types = {q["area_type"] for q in queues}
    assert "SECURITY_TSA" in area_types
    assert "SECURITY_PRECHECK" in area_types
    for q in queues:
        assert "wait_min" in q
        assert "sla_status" in q


def test_recommendations_returns_prioritised_actions() -> None:
    with _client() as client:
        response = client.get("/operations/recommendations")

    assert response.status_code == 200
    recs = response.json()["recommendations"]
    assert len(recs) > 0
    for r in recs:
        assert r["priority"] in ("HIGH", "MEDIUM", "LOW")
        assert r["airport_code"] in ("ATL", "DEN", "ORD", "LAX", "DFW")
        assert "action" in r
        assert "reason" in r


def test_heatmap_returns_cells() -> None:
    with _client() as client:
        response = client.get(
            "/queues/heatmap", params={"airport": "ATL", "area": "SECURITY_TSA"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["airport_code"] == "ATL"
    assert data["area_type"] == "SECURITY_TSA"
    assert len(data["cells"]) > 0
    cell = data["cells"][0]
    assert "day_of_week" in cell
    assert "hour" in cell
    assert "avg_wait_min" in cell


def test_airports_returns_all_five() -> None:
    with _client() as client:
        response = client.get("/airports")

    assert response.status_code == 200
    airports = response.json()["airports"]
    codes = {a["airport_code"] for a in airports}
    assert codes == {"ATL", "DEN", "ORD", "LAX", "DFW"}
    for a in airports:
        assert "lat" in a
        assert "lon" in a
        assert "sla_status" in a


def test_anomalies_recent_returns_events() -> None:
    with _client() as client:
        response = client.get("/anomalies/recent", params={"hours": 720})

    assert response.status_code == 200
    events = response.json()["events"]
    assert len(events) > 0
    for e in events:
        assert e["severity"] in ("LOW", "MEDIUM", "HIGH")
        assert e["anomaly_type"] in ("SPIKE", "DROP", "CROSS_AIRPORT", "SEASONAL")


def test_models_returns_three() -> None:
    with _client() as client:
        response = client.get("/models")

    assert response.status_code == 200
    models = response.json()["models"]
    names = [m["name"] for m in models]
    assert names == ["prophet", "nbeats", "lstm"]
    default = [m for m in models if m["default"]]
    assert len(default) == 1


def test_shift_handoff_returns_briefing() -> None:
    with _client() as client:
        response = client.get(
            "/operations/shift-handoff", params={"airport": "ATL", "shift_hours": 8},
        )

    assert response.status_code == 200
    data = response.json()
    handoffs = data["handoffs"]
    assert len(handoffs) >= 1
    h = handoffs[0]
    assert h["airport_code"] == "ATL"
    assert h["total_pax"] > 0
    assert "summary" in h
    assert "next_shift_outlook" in h


def test_airport_terminals_returns_breakdown() -> None:
    with _client() as client:
        response = client.get("/airports/ATL/terminals")

    assert response.status_code == 200
    data = response.json()
    assert data["airport_code"] == "ATL"
    terminals = data["terminals"]
    assert len(terminals) == 2
    names = {t["terminal"] for t in terminals}
    assert "T-North" in names
    assert "T-South" in names
    for t in terminals:
        assert t["sla_status"] in ("OK", "WARNING", "BREACH")


def test_capacity_utilization() -> None:
    with _client() as client:
        response = client.get("/airports/ATL/capacity")

    assert response.status_code == 200
    data = response.json()
    assert data["airport_code"] == "ATL"
    assert 0 <= data["overall_utilization_pct"] <= 100
    assert len(data["areas"]) > 0
    for a in data["areas"]:
        assert a["status"] in ("LOW", "MODERATE", "HIGH", "CRITICAL")
        assert a["current_throughput"] >= 0


def test_daily_scorecard() -> None:
    with _client() as client:
        response = client.get(
            "/airports/ATL/scorecard", params={"target_date": "2021-11-24"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["airport_code"] == "ATL"
    assert data["overall_score"] in ("EXCELLENT", "GOOD", "FAIR", "POOR")
    assert data["total_pax"] > 0
    assert len(data["areas"]) > 0


def test_network_health() -> None:
    with _client() as client:
        response = client.get("/network/health")

    assert response.status_code == 200
    data = response.json()
    assert 0 <= data["network_score"] <= 100
    assert data["network_grade"] in ("A", "B", "C", "D", "F")
    assert len(data["airports"]) == 5
    for a in data["airports"]:
        assert a["airport_code"] in ("ATL", "DEN", "ORD", "LAX", "DFW")
        assert a["grade"] in ("A", "B", "C", "D", "F")
