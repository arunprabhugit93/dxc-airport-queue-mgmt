const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

async function get<T>(path: string, params?: Record<string, string>): Promise<T> {
  const url = new URL(`${API_BASE}${path}`);
  if (params) {
    Object.entries(params).forEach(([k, v]) => url.searchParams.set(k, v));
  }
  const res = await fetch(url.toString(), { cache: "no-store" });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `API error ${res.status}`);
  }
  return res.json();
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    cache: "no-store",
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || `API error ${res.status}`);
  }
  return res.json();
}

// Types
export interface Airport {
  airport_code: string;
  name: string;
  lat: number;
  lon: number;
  worst_wait_min: number;
  sla_status: string;
  active_anomalies: number;
  total_pax_today: number;
}

export interface QueueItem {
  airport_code: string;
  area_type: string;
  pax_last_hour: number;
  lanes_open: number;
  wait_min: number;
  sla_status: string;
  predicted_breach_in_min: number | null;
  trend: string;
}

export interface ForecastPoint {
  target_ts: string;
  horizon_min: number;
  pred_wait_min: number;
  pred_throughput: number | null;
  lower_min: number | null;
  upper_min: number | null;
}

export interface AnomalyEvent {
  event_id: number;
  airport_code: string;
  area_type: string | null;
  detected_at: string;
  anomaly_type: string;
  detector: string;
  metric: string;
  observed_value: number;
  expected_value: number | null;
  score: number;
  severity: string;
  description: string | null;
}

export interface JourneyStage {
  stage: string;
  avg_wait_min: number;
  queue_length: number;
  status: string;
}

export interface Recommendation {
  priority: string;
  airport_code: string;
  area: string;
  action: string;
  reason: string;
  impact: string;
}

export interface HeatmapCell {
  day_of_week: number;
  hour: number;
  avg_wait_min: number;
  avg_pax: number;
}

export interface StaffingHour {
  rec_hour: number;
  forecast_pax: number;
  recommended_lanes: number;
  recommended_staff: number;
  expected_wait_min: number;
  sla_met: boolean;
}

export interface NetworkAirportHealth {
  airport_code: string;
  health_score: number;
  sla_compliance_pct: number;
  avg_wait_min: number;
  anomaly_count: number;
  grade: string;
}

export interface EnergyAirportSummary {
  airport_code: string;
  outdoor_temp_f: number;
  indoor_setpoint_f: number;
  current_load_kw: number;
  hvac_load_kw: number;
  daily_energy_kwh: number;
  daily_cost_usd: number;
  carbon_kg: number;
  peak_risk: string;
  savings_opportunity_pct: number;
}

export interface EnergyTerminalStatus {
  terminal: string;
  occupancy_index: number;
  outdoor_temp_f: number;
  indoor_setpoint_f: number;
  current_load_kw: number;
  hvac_load_kw: number;
  lighting_load_kw: number;
  plug_load_kw: number;
  charging_load_kw: number;
  comfort_status: string;
  optimization_action: string;
}

export interface EnergyTemperaturePoint {
  hour: number;
  outdoor_temp_f: number;
  occupancy_index: number;
  hvac_load_kw: number;
  total_load_kw: number;
}

export interface EnergySetpointSimulation {
  airport_code: string;
  baseline_setpoint_f: number;
  scenario_setpoint_f: number;
  duration_hours: number;
  baseline_energy_kwh: number;
  scenario_energy_kwh: number;
  saved_energy_kwh: number;
  saved_cost_usd: number;
  carbon_reduction_kg: number;
  comfort_risk: string;
  recommendation: string;
}

export interface EnergyRecommendation {
  priority: string;
  airport_code: string;
  area: string;
  action: string;
  reason: string;
  estimated_savings_usd: number;
}

// API functions
export const api = {
  getHealth: () => get<{ status: string; db_loaded: boolean; models_loaded: string[]; demo_now: string }>("/health"),

  getAirports: () => get<{ as_of: string; airports: Airport[] }>("/airports"),

  getQueues: (airport?: string) => {
    const params: Record<string, string> = {};
    if (airport && airport !== "All") params.airport = airport;
    return get<{ as_of: string; queues: QueueItem[] }>("/queues/current", params);
  },

  getAllAreaQueues: (airport: string) =>
    get<{ as_of: string; queues: { airport_code: string; area_type: string; queue_length: number; wait_min: number; staff_on_duty: number; sla_status: string }[] }>("/queues/all-areas", { airport }),

  getForecast: (airport: string, horizon = 60, area = "SECURITY_TSA", model = "prophet") =>
    get<{ airport_code: string; area_type: string; model_name: string; origin_ts: string; horizon_min: number; points: ForecastPoint[] }>("/queues/forecast", { airport, horizon: String(horizon), area, model }),

  getAnomalies: (airport?: string, hours = 24) => {
    const params: Record<string, string> = { hours: String(hours) };
    if (airport && airport !== "All") params.airport = airport;
    return get<{ as_of: string; window_hours: number; events: AnomalyEvent[] }>("/anomalies/recent", params);
  },

  getStaffing: (airport: string, date: string, area = "SECURITY_TSA", sla_target = 10) =>
    get<{ airport_code: string; rec_date: string; area_type: string; sla_target_min: number; hours: StaffingHour[]; totals: { peak_lanes: number; total_staff_hours: number } }>("/staffing/recommend", { airport, date, area, sla_target: String(sla_target) }),

  simulateWhatIf: (body: Record<string, unknown>) =>
    post<{ scenario: Record<string, number>; baseline: Record<string, number>; delta: Record<string, number> }>("/simulate/what-if", body),

  getKpis: (dateFrom: string, dateTo: string, airport = "ALL") =>
    get<{ airport_code: string; date_from: string; date_to: string; kpis: Record<string, number | string>; trend: { obs_date: string; avg_wait_min: number; total_pax: number; sla_breach_rate: number }[] }>("/dashboard/kpis", { date_from: dateFrom, date_to: dateTo, airport }),

  getModels: () => get<{ models: { name: string; label: string; default: boolean; horizon_max_min: number }[] }>("/models"),

  getClock: () => get<{ demo_now: string; min: string; max: string }>("/config/clock"),
  setClock: (demo_now: string) => post<{ demo_now: string; min: string; max: string }>("/config/clock", { demo_now }),

  getJourney: (airport: string) =>
    get<{ airport_code: string; as_of: string; stages: JourneyStage[]; total_journey_min: number; bottleneck: string }>("/passenger-journey", { airport }),

  getRecommendations: (airport?: string) => {
    const params: Record<string, string> = {};
    if (airport && airport !== "All") params.airport = airport;
    return get<{ as_of: string; recommendations: Recommendation[] }>("/operations/recommendations", params);
  },

  getHeatmap: (airport: string, area = "SECURITY_TSA", days = 30) =>
    get<{ airport_code: string; area_type: string; cells: HeatmapCell[] }>("/queues/heatmap", { airport, area, days: String(days) }),

  getNetworkHealth: () =>
    get<{ as_of: string; network_score: number; network_grade: string; airports: NetworkAirportHealth[] }>("/network/health"),

  getShiftHandoff: (airport?: string) => {
    const params: Record<string, string> = {};
    if (airport && airport !== "All") params.airport = airport;
    return get<{ as_of: string; handoffs: { airport_code: string; shift_start: string; shift_end: string; summary: string; peak_wait_min: number; avg_wait_min: number; total_pax: number; anomalies_during_shift: number; sla_breaches: number; next_shift_outlook: string }[] }>("/operations/shift-handoff", params);
  },

  getCapacity: (airport: string) =>
    get<{ airport_code: string; as_of: string; overall_utilization_pct: number; areas: { area_type: string; current_throughput: number; max_capacity: number; utilization_pct: number; headroom_pax: number; status: string }[] }>(`/airports/${airport}/capacity`),

  getScorecard: (airport: string, date?: string) => {
    const params: Record<string, string> = {};
    if (date) params.target_date = date;
    return get<{ airport_code: string; date: string; overall_score: string; total_pax: number; avg_wait_min: number; sla_compliance_pct: number; anomaly_count: number; areas: { area_type: string; avg_wait_min: number; peak_wait_min: number; total_pax: number; sla_compliance_pct: number }[] }>(`/airports/${airport}/scorecard`, params);
  },

  getTerminals: (airport: string) =>
    get<{ airport_code: string; as_of: string; terminals: { terminal: string; estimated_pax: number; estimated_wait_min: number; sla_status: string }[] }>(`/airports/${airport}/terminals`),

  getEnergyOverview: (airport?: string) => {
    const params: Record<string, string> = {};
    if (airport && airport !== "All") params.airport = airport;
    return get<{ as_of: string; tariff_usd_per_kwh: number; network_load_kw: number; network_daily_cost_usd: number; network_carbon_kg: number; airports: EnergyAirportSummary[] }>("/energy/overview", params);
  },

  getEnergyTerminals: (airport: string) =>
    get<{ airport_code: string; as_of: string; terminals: EnergyTerminalStatus[] }>("/energy/terminals", { airport }),

  getEnergyTemperatureProfile: (airport: string) =>
    get<{ airport_code: string; as_of: string; points: EnergyTemperaturePoint[] }>("/energy/temperature-profile", { airport }),

  simulateEnergySetpoint: (body: Record<string, unknown>) =>
    post<EnergySetpointSimulation>("/energy/setpoint-simulation", body),

  getEnergyRecommendations: (airport?: string) => {
    const params: Record<string, string> = {};
    if (airport && airport !== "All") params.airport = airport;
    return get<{ as_of: string; recommendations: EnergyRecommendation[] }>("/energy/recommendations", params);
  },
};

export const AIRPORT_CODES = ["ATL", "DEN", "ORD", "LAX", "DFW"];

export const AREA_LABELS: Record<string, string> = {
  CHECKIN: "Check-in",
  SECURITY_TSA: "Security (TSA)",
  SECURITY_PRECHECK: "PreCheck",
  IMMIGRATION: "Immigration",
  GATE: "Gate",
  BAGGAGE: "Baggage",
};

export const SLA_COLORS: Record<string, string> = {
  OK: "#2EA043",
  WARNING: "#D29922",
  BREACH: "#F85149",
};

export const SEVERITY_COLORS: Record<string, string> = {
  LOW: "#636B74",
  MEDIUM: "#D29922",
  HIGH: "#F85149",
};

export const GRADE_COLORS: Record<string, string> = {
  A: "#2EA043",
  B: "#58A6FF",
  C: "#D29922",
  D: "#DB6D28",
  F: "#F85149",
};
