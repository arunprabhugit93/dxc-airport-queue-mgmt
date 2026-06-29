"use client";

import { useState } from "react";
import { api, AIRPORT_CODES, AREA_LABELS } from "@/lib/api";
import { MetricCard } from "@/components/metric-card";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from "@/components/ui/select";
import { Slider } from "@/components/ui/slider";
import { Switch } from "@/components/ui/switch";
import { FlaskConical, Play, ArrowUp, ArrowDown, Minus } from "lucide-react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from "recharts";

interface SimResults {
  scenario: Record<string, number>;
  baseline: Record<string, number>;
  delta: Record<string, number>;
}

const METRIC_LABELS: Record<string, string> = {
  mean_wait: "Mean Wait (min)",
  p95_wait: "P95 Wait (min)",
  max_queue_len: "Max Queue Length",
  lane_utilisation: "Lane Utilisation",
  sla_breach_min: "SLA Breach (min)",
};

export default function SimulatorPage() {
  const [airport, setAirport] = useState("ATL");
  const [area, setArea] = useState("SECURITY_TSA");
  const [lanes, setLanes] = useState(5);
  const [precheckRatio, setPrecheckRatio] = useState(0.3);
  const [serviceRate, setServiceRate] = useState("2.5");
  const [surgeMultiplier, setSurgeMultiplier] = useState(1.0);
  const [duration, setDuration] = useState(60);
  const [useCurrent, setUseCurrent] = useState(false);
  const [results, setResults] = useState<SimResults | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function runSimulation() {
    setLoading(true);
    setError(null);
    try {
      const body: Record<string, unknown> = {
        airport,
        area,
        lanes,
        precheck_ratio: precheckRatio,
        service_rate: parseFloat(serviceRate) || 2.5,
        surge_multiplier: surgeMultiplier,
        duration_min: duration,
        use_current_arrivals: useCurrent,
      };
      const data = await api.simulateWhatIf(body);
      setResults(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Simulation failed");
    } finally {
      setLoading(false);
    }
  }

  const comparisonMetrics = results
    ? Object.keys(METRIC_LABELS).filter((k) => k in results.baseline || k in results.scenario)
    : [];

  const chartData = comparisonMetrics.map((key) => ({
    metric: METRIC_LABELS[key] || key,
    Baseline: results?.baseline[key] ?? 0,
    Scenario: results?.scenario[key] ?? 0,
  }));

  // Verdict: improvement if mean_wait decreased
  const isImprovement = results
    ? (results.delta.mean_wait ?? 0) < 0
    : false;

  function getDeltaArrow(delta: number) {
    if (delta < -0.01) return <ArrowDown className="h-4 w-4 text-green-400 inline" />;
    if (delta > 0.01) return <ArrowUp className="h-4 w-4 text-red-400 inline" />;
    return <Minus className="h-4 w-4 text-muted-foreground inline" />;
  }

  function getDeltaColor(key: string, delta: number) {
    // For utilisation, higher can be neutral; for waits/breaches, lower is better
    if (key === "lane_utilisation") return delta > 0 ? "#58A6FF" : "#8B949E";
    return delta < 0 ? "#2EA043" : delta > 0 ? "#F85149" : "#8B949E";
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center gap-2 mb-2">
        <FlaskConical className="h-6 w-6 text-purple-500" />
        <h1 className="text-2xl font-bold text-foreground">What-If Scenario Simulator</h1>
      </div>

      {/* Control Panel */}
      <Card>
        <CardHeader>
          <CardTitle>Simulation Parameters</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="flex flex-col gap-1">
              <label className="text-xs text-muted-foreground uppercase tracking-wider">Airport</label>
              <Select value={airport} onValueChange={(v) => v && setAirport(v)}>
                <SelectTrigger className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {AIRPORT_CODES.map((c) => (
                    <SelectItem key={c} value={c}>{c}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="flex flex-col gap-1">
              <label className="text-xs text-muted-foreground uppercase tracking-wider">Area</label>
              <Select value={area} onValueChange={(v) => v && setArea(v)}>
                <SelectTrigger className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {Object.entries(AREA_LABELS).map(([key, label]) => (
                    <SelectItem key={key} value={key}>{label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="flex flex-col gap-1">
              <label className="text-xs text-muted-foreground uppercase tracking-wider">
                Lanes: {lanes}
              </label>
              <Slider
                min={1}
                max={20}
                value={[lanes]}
                onValueChange={(v) => setLanes(Array.isArray(v) ? v[0] : v)}
              />
            </div>

            <div className="flex flex-col gap-1">
              <label className="text-xs text-muted-foreground uppercase tracking-wider">
                PreCheck Ratio: {precheckRatio.toFixed(2)}
              </label>
              <Slider
                min={0}
                max={100}
                value={[precheckRatio * 100]}
                onValueChange={(v) => setPrecheckRatio((Array.isArray(v) ? v[0] : v) / 100)}
              />
            </div>

            <div className="flex flex-col gap-1">
              <label className="text-xs text-muted-foreground uppercase tracking-wider">
                Service Rate (pax/min)
              </label>
              <input
                type="number"
                step="0.1"
                min="0.1"
                value={serviceRate}
                onChange={(e) => setServiceRate(e.target.value)}
                className="h-8 rounded-lg border border-input bg-transparent px-2.5 text-sm text-foreground outline-none focus:border-ring focus:ring-3 focus:ring-ring/50"
              />
            </div>

            <div className="flex flex-col gap-1">
              <label className="text-xs text-muted-foreground uppercase tracking-wider">
                Surge Multiplier: {surgeMultiplier.toFixed(1)}x
              </label>
              <Slider
                min={5}
                max={30}
                value={[surgeMultiplier * 10]}
                onValueChange={(v) => setSurgeMultiplier((Array.isArray(v) ? v[0] : v) / 10)}
              />
            </div>

            <div className="flex flex-col gap-1">
              <label className="text-xs text-muted-foreground uppercase tracking-wider">
                Duration: {duration} min
              </label>
              <Slider
                min={15}
                max={240}
                step={15}
                value={[duration]}
                onValueChange={(v) => setDuration(Array.isArray(v) ? v[0] : v)}
              />
            </div>

            <div className="flex items-center gap-3">
              <Switch
                checked={useCurrent}
                onCheckedChange={(checked) => setUseCurrent(checked)}
              />
              <label className="text-sm text-foreground">Use current arrivals</label>
            </div>
          </div>

          <div className="mt-6 flex justify-end">
            <Button onClick={runSimulation} disabled={loading} size="lg">
              <Play className="h-4 w-4 mr-2" />
              {loading ? "Running..." : "Run Simulation"}
            </Button>
          </div>
        </CardContent>
      </Card>

      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 text-red-400">
          {error}
        </div>
      )}

      {loading && (
        <div className="flex items-center justify-center h-32 text-muted-foreground">
          <div className="animate-pulse">Running simulation...</div>
        </div>
      )}

      {results && !loading && (
        <>
          {/* Verdict Callout */}
          <div className={`rounded-lg p-4 border ${isImprovement ? "bg-green-500/10 border-green-500/30" : "bg-red-500/10 border-red-500/30"}`}>
            <div className="flex items-center gap-2">
              {isImprovement ? (
                <ArrowDown className="h-5 w-5 text-green-400" />
              ) : (
                <ArrowUp className="h-5 w-5 text-red-400" />
              )}
              <span className={`text-lg font-semibold ${isImprovement ? "text-green-400" : "text-red-400"}`}>
                {isImprovement ? "Improvement" : "Degradation"} Detected
              </span>
            </div>
            <p className="text-sm text-muted-foreground mt-1">
              Mean wait {isImprovement ? "decreased" : "increased"} by {Math.abs(results.delta.mean_wait ?? 0).toFixed(1)} min
              {results.delta.p95_wait !== undefined && (
                <> &middot; P95 wait {(results.delta.p95_wait ?? 0) < 0 ? "decreased" : "increased"} by {Math.abs(results.delta.p95_wait ?? 0).toFixed(1)} min</>
              )}
            </p>
          </div>

          {/* Baseline vs Scenario Comparison */}
          <div className="space-y-3">
            <h2 className="text-lg font-semibold text-foreground">Baseline vs Scenario</h2>
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
              {comparisonMetrics.map((key) => {
                const baseline = results.baseline[key] ?? 0;
                const scenario = results.scenario[key] ?? 0;
                const delta = results.delta[key] ?? 0;
                const format = key === "lane_utilisation"
                  ? (v: number) => `${(v * 100).toFixed(0)}%`
                  : (v: number) => v.toFixed(1);
                return (
                  <div key={key} className="space-y-2">
                    <MetricCard
                      label={`${METRIC_LABELS[key] || key} (Baseline)`}
                      value={format(baseline)}
                      accentColor="#F85149"
                    />
                    <MetricCard
                      label={`${METRIC_LABELS[key] || key} (Scenario)`}
                      value={format(scenario)}
                      sublabel={
                        `${delta >= 0 ? "+" : ""}${format(delta)}`
                      }
                      accentColor="#58A6FF"
                    />
                    <div className="text-center text-sm" style={{ color: getDeltaColor(key, delta) }}>
                      {getDeltaArrow(delta)} {delta >= 0 ? "+" : ""}{format(delta)}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Comparison Bar Chart */}
          <Card>
            <CardHeader>
              <CardTitle>Metric Comparison</CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={350}>
                <BarChart data={chartData} margin={{ top: 10, right: 20, bottom: 40, left: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#2D3139" />
                  <XAxis
                    dataKey="metric"
                    tick={{ fill: "#8B949E", fontSize: 11 }}
                    angle={-20}
                    textAnchor="end"
                    stroke="#2D3139"
                  />
                  <YAxis tick={{ fill: "#8B949E", fontSize: 12 }} stroke="#2D3139" />
                  <Tooltip
                    contentStyle={{ backgroundColor: "var(--card)", border: "1px solid var(--border)", borderRadius: 8 }}
                    labelStyle={{ color: "var(--foreground)" }}
                  />
                  <Legend />
                  <Bar dataKey="Baseline" fill="#F85149" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="Scenario" fill="#58A6FF" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
