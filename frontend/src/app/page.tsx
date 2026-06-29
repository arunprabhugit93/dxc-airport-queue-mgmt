"use client";

import { useEffect, useState } from "react";
import { useClock } from "@/components/clock-context";
import {
  api,
  AIRPORT_CODES,
  AREA_LABELS,
  SLA_COLORS,
  SEVERITY_COLORS,
  GRADE_COLORS,
} from "@/lib/api";
import type {
  Airport,
  QueueItem,
  AnomalyEvent,
  Recommendation,
  ForecastPoint,
} from "@/lib/api";
import { MetricCard } from "@/components/metric-card";
import { StatusBadge } from "@/components/status-badge";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from "@/components/ui/select";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";
import {
  AlertTriangle,
  TrendingUp,
  TrendingDown,
  Minus,
  CheckCircle2,
  RefreshCw,
} from "lucide-react";
import { useAutoRefresh } from "@/lib/use-auto-refresh";

function TrendArrow({ trend }: { trend: string }) {
  if (trend === "UP") return <TrendingUp className="h-4 w-4 text-red-500 inline" />;
  if (trend === "DOWN") return <TrendingDown className="h-4 w-4 text-green-500 inline" />;
  return <Minus className="h-4 w-4 text-gray-500 inline" />;
}

function buildNarrative(
  grade: string,
  score: number,
  breachQueues: QueueItem[],
  highAnomalies: AnomalyEvent[],
  airports: Airport[],
  topRec: Recommendation | undefined,
): { text: string; level: "ok" | "warn" | "critical" } {
  const breachCount = breachQueues.length;
  const worstAirport = airports.length
    ? airports.slice().sort((a, b) => b.worst_wait_min - a.worst_wait_min)[0]
    : null;

  if (breachCount === 0 && highAnomalies.length === 0) {
    return {
      text: `Network at ${grade} (${score.toFixed(0)}/100) — all ${airports.length} airports within SLA, no high-priority alerts.`,
      level: "ok",
    };
  }
  if (breachCount >= 3) {
    const action = topRec ? ` Priority: ${topRec.action.toLowerCase()}.` : "";
    return {
      text: `Critical: ${breachCount} active SLA breaches across the network. ${worstAirport ? `${worstAirport.airport_code} is worst at ${worstAirport.worst_wait_min.toFixed(0)} min.` : ""}${action} Immediate intervention required.`,
      level: "critical",
    };
  }
  if (breachCount > 0) {
    const breachAirports = [...new Set(breachQueues.map((q) => q.airport_code))].join(", ");
    const action = topRec ? ` Recommended: ${topRec.action.toLowerCase()}.` : "";
    return {
      text: `${breachCount} SLA breach${breachCount > 1 ? "es" : ""} active at ${breachAirports}.${action}`,
      level: "critical",
    };
  }
  if (highAnomalies.length > 0) {
    return {
      text: `Network at ${score.toFixed(0)}/100 with ${highAnomalies.length} high-priority anomal${highAnomalies.length > 1 ? "ies" : "y"} under investigation. No active SLA breaches.`,
      level: "warn",
    };
  }
  return {
    text: `Network at ${grade} (${score.toFixed(0)}/100) with minor warnings. ${worstAirport ? `${worstAirport.airport_code} is the closest to threshold at ${worstAirport.worst_wait_min.toFixed(1)} min — monitor closely.` : ""}`,
    level: "warn",
  };
}

const REFRESH_OPTIONS: { label: string; value: number | null }[] = [
  { label: "Off", value: null },
  { label: "30s", value: 30 },
  { label: "60s", value: 60 },
];

export default function CommandCenter() {
  const { demoNow } = useClock();
  const [airport, setAirport] = useState("All");
  const [refreshInterval, setRefreshInterval] = useState<number | null>(null);
  const refreshTick = useAutoRefresh(refreshInterval);

  const [networkScore, setNetworkScore] = useState<number>(0);
  const [networkGrade, setNetworkGrade] = useState<string>("—");
  const [anomalies, setAnomalies] = useState<AnomalyEvent[]>([]);
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [airports, setAirports] = useState<Airport[]>([]);
  const [queues, setQueues] = useState<QueueItem[]>([]);
  const [forecast, setForecast] = useState<ForecastPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const [healthRes, anomRes, recRes, airRes, qRes] = await Promise.all([
          api.getNetworkHealth(),
          api.getAnomalies(airport === "All" ? undefined : airport),
          api.getRecommendations(airport === "All" ? undefined : airport),
          api.getAirports(),
          api.getQueues(airport === "All" ? undefined : airport),
        ]);
        if (cancelled) return;
        setNetworkScore(healthRes.network_score);
        setNetworkGrade(healthRes.network_grade);
        setAnomalies(anomRes.events);
        setRecommendations(recRes.recommendations);
        setAirports(airRes.airports);
        setQueues(qRes.queues);

        const forecastAirport = airport !== "All" ? airport : AIRPORT_CODES[0];
        try {
          const fcRes = await api.getForecast(forecastAirport, 60);
          if (!cancelled) setForecast(fcRes.points);
        } catch {
          if (!cancelled) setForecast([]);
        }
      } catch (err) {
        if (!cancelled)
          setError(err instanceof Error ? err.message : "Failed to load data");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [demoNow, airport, refreshTick]);

  const highAnomalies = anomalies.filter((a) => a.severity === "HIGH");
  const breachQueues = queues.filter((q) => q.sla_status === "BREACH");
  const worstWait = airports.length
    ? Math.max(...airports.map((a) => a.worst_wait_min))
    : 0;
  const breachCount = breachQueues.length;
  const activeAnomalies = anomalies.length;
  const totalPax = airports.reduce((s, a) => s + a.total_pax_today, 0);
  const highRecs = recommendations.filter((r) => r.priority === "HIGH");
  const otherRecs = recommendations.filter((r) => r.priority !== "HIGH");

  const narrative = buildNarrative(
    networkGrade,
    networkScore,
    breachQueues,
    highAnomalies,
    airports,
    recommendations[0],
  );

  const narrativeBorder =
    narrative.level === "critical"
      ? "border-red-500/40 bg-red-500/5"
      : narrative.level === "warn"
        ? "border-yellow-500/40 bg-yellow-500/5"
        : "border-green-500/40 bg-green-500/5";

  const NarrativeIcon =
    narrative.level === "ok" ? (
      <CheckCircle2 className="h-5 w-5 text-green-500 shrink-0" />
    ) : (
      <AlertTriangle
        className={`h-5 w-5 shrink-0 ${narrative.level === "critical" ? "text-red-500" : "text-yellow-500"}`}
      />
    );

  if (error) {
    return (
      <div className="flex items-center justify-center h-96">
        <Card className="max-w-md w-full">
          <CardContent className="pt-6">
            <div className="flex items-center gap-2 text-red-500 mb-2">
              <AlertTriangle className="h-5 w-5" />
              <span className="font-semibold">Error</span>
            </div>
            <p className="text-muted-foreground text-sm">{error}</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <h1 className="text-2xl font-bold">Command Center</h1>
        <div className="flex items-center gap-3 flex-wrap">
          <div className="flex items-center gap-2">
            <RefreshCw
              className={`h-3.5 w-3.5 text-muted-foreground ${refreshInterval ? "animate-spin" : ""}`}
              style={refreshInterval ? { animationDuration: "3s" } : undefined}
            />
            <span className="text-xs text-muted-foreground">Auto-refresh:</span>
            <div className="flex rounded-md border border-border overflow-hidden text-xs">
              {REFRESH_OPTIONS.map((opt) => (
                <button
                  key={String(opt.value)}
                  onClick={() => setRefreshInterval(opt.value)}
                  className={`px-2.5 py-1 transition-colors ${
                    refreshInterval === opt.value
                      ? "bg-blue-600 text-white"
                      : "bg-card text-muted-foreground hover:text-foreground hover:bg-muted"
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>
          <Select value={airport} onValueChange={(v) => v && setAirport(v)}>
            <SelectTrigger className="w-40">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="All">All Airports</SelectItem>
              {AIRPORT_CODES.map((code) => (
                <SelectItem key={code} value={code}>
                  {code}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {loading ? (
        <div className="text-muted-foreground py-20 text-center">Loading…</div>
      ) : (
        <>
          {/* Situation Narrative */}
          <Card className={`border ${narrativeBorder}`}>
            <CardContent className="flex items-center gap-3 py-4">
              {NarrativeIcon}
              <p className="text-sm font-medium leading-relaxed">{narrative.text}</p>
            </CardContent>
          </Card>

          {/* Airport Status Grid */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                Airport Status
              </h2>
              <div className="flex items-center gap-3 text-[10px] text-muted-foreground">
                <span className="flex items-center gap-1">
                  <span className="w-2 h-2 rounded-full bg-green-500 inline-block" />
                  OK
                </span>
                <span className="flex items-center gap-1">
                  <span className="w-2 h-2 rounded-full bg-yellow-500 inline-block" />
                  Warning
                </span>
                <span className="flex items-center gap-1">
                  <span className="w-2 h-2 rounded-full bg-red-500 inline-block" />
                  Breach
                </span>
              </div>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
              {airports.map((ap) => {
                const borderCls =
                  ap.sla_status === "BREACH"
                    ? "border-red-500/50 bg-red-500/5"
                    : ap.sla_status === "WARNING"
                      ? "border-yellow-500/50 bg-yellow-500/5"
                      : "border-green-500/20";
                const dotCls =
                  ap.sla_status === "BREACH"
                    ? "bg-red-500"
                    : ap.sla_status === "WARNING"
                      ? "bg-yellow-500"
                      : "bg-green-500";
                const selected = airport === ap.airport_code;
                return (
                  <button
                    key={ap.airport_code}
                    onClick={() => setAirport(selected ? "All" : ap.airport_code)}
                    className={`text-left rounded-lg border p-3 transition-all hover:bg-muted/50 ${borderCls} ${selected ? "ring-2 ring-blue-500" : ""}`}
                  >
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="font-bold text-sm">{ap.airport_code}</span>
                      <span className={`w-2 h-2 rounded-full ${dotCls}`} />
                    </div>
                    <div className="text-xl font-bold font-mono leading-none">
                      {ap.worst_wait_min.toFixed(1)}
                      <span className="text-xs font-normal text-muted-foreground ml-0.5">
                        m
                      </span>
                    </div>
                    <div className="text-[10px] text-muted-foreground mt-1.5">
                      {ap.total_pax_today.toLocaleString()} pax today
                    </div>
                    {ap.active_anomalies > 0 && (
                      <div className="text-[10px] text-yellow-500 mt-0.5">
                        {ap.active_anomalies} anomal
                        {ap.active_anomalies === 1 ? "y" : "ies"}
                      </div>
                    )}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Priority Actions — HIGH only, prominent */}
          {highRecs.length > 0 && (
            <div>
              <h2 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">
                Priority Actions
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {highRecs.slice(0, 4).map((r, i) => (
                  <Card key={i} className="border-red-500/40 bg-red-500/5">
                    <CardContent className="flex items-start gap-3 py-4">
                      <AlertTriangle className="h-4 w-4 text-red-500 mt-0.5 shrink-0" />
                      <div className="min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-xs font-bold text-red-500">
                            {r.airport_code}
                          </span>
                          <span className="text-xs text-muted-foreground">
                            {AREA_LABELS[r.area] || r.area}
                          </span>
                        </div>
                        <p className="text-sm font-semibold">{r.action}</p>
                        <p className="text-xs text-muted-foreground mt-1">
                          {r.reason}
                        </p>
                        <p className="text-xs text-blue-400 mt-1.5">
                          Expected impact: {r.impact}
                        </p>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </div>
          )}

          {/* Other recommendations — quieter */}
          {highRecs.length === 0 && otherRecs.length > 0 && (
            <div>
              <h2 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">
                Recommendations
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                {otherRecs.slice(0, 3).map((r, i) => (
                  <Card key={i}>
                    <CardContent className="py-4">
                      <div className="flex items-center gap-2 mb-2">
                        <StatusBadge status={r.priority} />
                        <span className="text-xs text-muted-foreground">
                          {r.airport_code} · {AREA_LABELS[r.area] || r.area}
                        </span>
                      </div>
                      <p className="text-sm font-medium">{r.action}</p>
                      <p className="text-xs text-muted-foreground mt-1">
                        {r.reason}
                      </p>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </div>
          )}

          {/* KPI Row */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <MetricCard
              label="Network Grade"
              value={`${networkGrade} · ${networkScore.toFixed(0)}`}
              accentColor={GRADE_COLORS[networkGrade] || "#636B74"}
              sublabel="Health score /100"
            />
            <MetricCard
              label="SLA Breaches"
              value={breachCount}
              accentColor={breachCount > 0 ? SLA_COLORS.BREACH : SLA_COLORS.OK}
              sublabel="Checkpoints in breach"
            />
            <MetricCard
              label="Active Anomalies"
              value={activeAnomalies}
              accentColor={
                activeAnomalies > 0 ? SEVERITY_COLORS.MEDIUM : "#636B74"
              }
              sublabel="Last 24 hours"
            />
            <MetricCard
              label="Total Passengers"
              value={totalPax.toLocaleString()}
              accentColor="#58A6FF"
              sublabel="Today across network"
            />
          </div>

          {/* Live Queue Table */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                Live Queue Status
                {refreshInterval && (
                  <span className="text-xs font-normal text-muted-foreground">
                    · auto-refreshing every {refreshInterval}s
                  </span>
                )}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border text-muted-foreground text-xs uppercase tracking-wider">
                      <th className="text-left py-3 px-2">Airport</th>
                      <th className="text-left py-3 px-2">Area</th>
                      <th className="text-right py-3 px-2">Lanes</th>
                      <th className="text-right py-3 px-2">Pax/hr</th>
                      <th className="text-right py-3 px-2">Wait</th>
                      <th className="text-center py-3 px-2">SLA</th>
                      <th className="text-center py-3 px-2">Trend</th>
                      <th className="text-right py-3 px-2">Breach In</th>
                    </tr>
                  </thead>
                  <tbody>
                    {queues.map((q, i) => (
                      <tr
                        key={`${q.airport_code}-${q.area_type}-${i}`}
                        className={`border-b border-border/50 hover:bg-muted/30 ${q.sla_status === "BREACH" ? "bg-red-500/5" : ""}`}
                      >
                        <td className="py-2.5 px-2 font-medium">
                          {q.airport_code}
                        </td>
                        <td className="py-2.5 px-2 text-muted-foreground">
                          {AREA_LABELS[q.area_type] || q.area_type}
                        </td>
                        <td className="py-2.5 px-2 text-right">{q.lanes_open}</td>
                        <td className="py-2.5 px-2 text-right font-mono text-muted-foreground">
                          {q.pax_last_hour.toLocaleString()}
                        </td>
                        <td
                          className="py-2.5 px-2 text-right font-mono font-semibold"
                          style={{
                            color:
                              q.sla_status === "BREACH"
                                ? SLA_COLORS.BREACH
                                : q.sla_status === "WARNING"
                                  ? SLA_COLORS.WARNING
                                  : undefined,
                          }}
                        >
                          {q.wait_min.toFixed(1)} min
                        </td>
                        <td className="py-2.5 px-2 text-center">
                          <StatusBadge status={q.sla_status} />
                        </td>
                        <td className="py-2.5 px-2 text-center">
                          <TrendArrow trend={q.trend} />
                        </td>
                        <td className="py-2.5 px-2 text-right text-xs">
                          {q.predicted_breach_in_min === 0 ? (
                            <span className="text-red-500 font-bold">NOW</span>
                          ) : q.predicted_breach_in_min != null ? (
                            <span className="text-muted-foreground">
                              {q.predicted_breach_in_min}m
                            </span>
                          ) : (
                            <span className="text-muted-foreground">—</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {queues.length === 0 && (
                  <p className="text-center text-muted-foreground text-sm py-8">
                    No queue data available for this selection.
                  </p>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Mini Forecast */}
          {forecast.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">
                  60-Min Wait Forecast{" "}
                  <span className="text-sm font-normal text-muted-foreground">
                    ({airport !== "All" ? airport : AIRPORT_CODES[0]} · Security
                    TSA)
                  </span>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={forecast}>
                      <CartesianGrid
                        strokeDasharray="3 3"
                        stroke="#2D3139"
                      />
                      <XAxis
                        dataKey="horizon_min"
                        tick={{ fill: "#8B949E", fontSize: 12 }}
                        tickFormatter={(v: number) => `+${v}m`}
                      />
                      <YAxis
                        tick={{ fill: "#8B949E", fontSize: 12 }}
                        tickFormatter={(v: number) => `${v}m`}
                      />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: "#161B22",
                          border: "1px solid #30363D",
                          borderRadius: 8,
                        }}
                        labelFormatter={(v) => `+${v} min`}
                        formatter={(v) => [
                          `${Number(v).toFixed(1)} min`,
                          "Predicted Wait",
                        ]}
                      />
                      <ReferenceLine
                        y={10}
                        stroke="#F85149"
                        strokeDasharray="4 4"
                        label={{ value: "SLA 10m", fill: "#F85149", fontSize: 11 }}
                      />
                      <Line
                        type="monotone"
                        dataKey="pred_wait_min"
                        stroke="#0080FF"
                        strokeWidth={2}
                        dot={false}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
