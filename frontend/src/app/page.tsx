"use client";

import { useEffect, useState } from "react";
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
  ShieldAlert,
  Users,
  Clock,
  Activity,
} from "lucide-react";

function TrendArrow({ trend }: { trend: string }) {
  if (trend === "UP")
    return <TrendingUp className="h-4 w-4 text-red-500 inline" />;
  if (trend === "DOWN")
    return <TrendingDown className="h-4 w-4 text-green-500 inline" />;
  return <Minus className="h-4 w-4 text-gray-500 inline" />;
}

export default function CommandCenter() {
  const [airport, setAirport] = useState("All");
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

        // Fetch forecast for first available airport
        const forecastAirport =
          airport !== "All" ? airport : AIRPORT_CODES[0];
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
  }, [airport]);

  const highAnomalies = anomalies.filter((a) => a.severity === "HIGH");
  const worstWait = airports.length
    ? Math.max(...airports.map((a) => a.worst_wait_min))
    : 0;
  const breachCount = queues.filter((q) => q.sla_status === "BREACH").length;
  const activeAnomalies = anomalies.length;
  const totalPax = airports.reduce((s, a) => s + a.total_pax_today, 0);

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
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Command Center</h1>
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

      {loading ? (
        <div className="text-muted-foreground py-20 text-center">
          Loading...
        </div>
      ) : (
        <>
          {/* Top row: Network Health + Alert Banners */}
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
            {/* Network Health Grade */}
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-6">
                <div
                  className="w-28 h-28 rounded-full flex items-center justify-center text-5xl font-bold text-white mb-2"
                  style={{
                    backgroundColor:
                      GRADE_COLORS[networkGrade] || "#636B74",
                  }}
                >
                  {networkGrade}
                </div>
                <div className="text-2xl font-bold mt-2">
                  {networkScore.toFixed(0)}
                  <span className="text-sm text-muted-foreground font-normal">
                    /100
                  </span>
                </div>
                <div className="text-xs text-muted-foreground mt-1">
                  Network Health
                </div>
              </CardContent>
            </Card>

            {/* High Severity Alert Banners */}
            <div className="lg:col-span-3 space-y-3">
              {highAnomalies.length === 0 ? (
                <Card>
                  <CardContent className="py-6 text-center text-muted-foreground">
                    <ShieldAlert className="h-8 w-8 mx-auto mb-2 text-green-500" />
                    No high-severity alerts
                  </CardContent>
                </Card>
              ) : (
                highAnomalies.slice(0, 3).map((a) => (
                  <Card
                    key={a.event_id}
                    className="border-red-500/50 bg-red-500/5"
                  >
                    <CardContent className="flex items-start gap-3 py-4">
                      <AlertTriangle className="h-5 w-5 text-red-500 mt-0.5 shrink-0" />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="font-semibold text-red-500">
                            {a.airport_code}
                          </span>
                          <span className="text-xs text-muted-foreground">
                            {a.area_type
                              ? AREA_LABELS[a.area_type] || a.area_type
                              : "Network"}
                          </span>
                          <StatusBadge status={a.severity} />
                        </div>
                        <p className="text-sm text-muted-foreground">
                          {a.description ||
                            `${a.anomaly_type}: ${a.metric} observed ${a.observed_value.toFixed(1)} (expected ${a.expected_value?.toFixed(1) ?? "N/A"})`}
                        </p>
                      </div>
                    </CardContent>
                  </Card>
                ))
              )}
            </div>
          </div>

          {/* Recommendations */}
          {recommendations.length > 0 && (
            <div>
              <h2 className="text-lg font-semibold mb-3">
                Actionable Recommendations
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {recommendations.slice(0, 6).map((r, i) => (
                  <Card key={i}>
                    <CardHeader>
                      <div className="flex items-center gap-2">
                        <CardTitle className="text-sm">{r.action}</CardTitle>
                        <StatusBadge status={r.priority} />
                      </div>
                    </CardHeader>
                    <CardContent>
                      <div className="text-xs text-muted-foreground mb-1">
                        {r.airport_code} &middot;{" "}
                        {AREA_LABELS[r.area] || r.area}
                      </div>
                      <p className="text-sm text-muted-foreground">
                        {r.reason}
                      </p>
                      <p className="text-xs text-blue-400 mt-2">
                        Impact: {r.impact}
                      </p>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </div>
          )}

          {/* KPI Metrics Row */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <MetricCard
              label="Worst Wait"
              value={`${worstWait.toFixed(0)} min`}
              accentColor={SLA_COLORS.BREACH}
              sublabel="Across all checkpoints"
            />
            <MetricCard
              label="SLA Breaches"
              value={breachCount}
              accentColor={
                breachCount > 0 ? SLA_COLORS.BREACH : SLA_COLORS.OK
              }
              sublabel="Checkpoints in breach"
            />
            <MetricCard
              label="Active Anomalies"
              value={activeAnomalies}
              accentColor={SEVERITY_COLORS.MEDIUM}
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
              <CardTitle>Live Queue Status</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border text-muted-foreground text-xs uppercase tracking-wider">
                      <th className="text-left py-3 px-2">Airport</th>
                      <th className="text-left py-3 px-2">Area</th>
                      <th className="text-right py-3 px-2">Lanes</th>
                      <th className="text-right py-3 px-2">Wait</th>
                      <th className="text-center py-3 px-2">SLA</th>
                      <th className="text-center py-3 px-2">Trend</th>
                    </tr>
                  </thead>
                  <tbody>
                    {queues.map((q, i) => (
                      <tr
                        key={`${q.airport_code}-${q.area_type}-${i}`}
                        className="border-b border-border/50 hover:bg-muted/30"
                      >
                        <td className="py-2.5 px-2 font-medium">
                          {q.airport_code}
                        </td>
                        <td className="py-2.5 px-2 text-muted-foreground">
                          {AREA_LABELS[q.area_type] || q.area_type}
                        </td>
                        <td className="py-2.5 px-2 text-right">
                          {q.lanes_open}
                        </td>
                        <td className="py-2.5 px-2 text-right font-mono">
                          {q.wait_min.toFixed(1)} min
                        </td>
                        <td className="py-2.5 px-2 text-center">
                          <StatusBadge status={q.sla_status} />
                        </td>
                        <td className="py-2.5 px-2 text-center">
                          <TrendArrow trend={q.trend} />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>

          {/* Mini Forecast Chart */}
          {forecast.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>
                  60-Minute Wait Forecast{" "}
                  <span className="text-sm font-normal text-muted-foreground">
                    ({airport !== "All" ? airport : AIRPORT_CODES[0]} &middot;
                    Security)
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
                        label={{
                          value: "SLA",
                          fill: "#F85149",
                          fontSize: 11,
                        }}
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
