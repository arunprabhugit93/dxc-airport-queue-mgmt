"use client";

import { useEffect, useState } from "react";
import {
  api,
  AIRPORT_CODES,
  AREA_LABELS,
  SLA_COLORS,
} from "@/lib/api";
import type { ForecastPoint } from "@/lib/api";
import { StatusBadge } from "@/components/status-badge";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from "@/components/ui/select";
import { Slider } from "@/components/ui/slider";
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";
import { AlertTriangle, Clock, TrendingUp } from "lucide-react";

const AREA_KEYS = Object.keys(AREA_LABELS);

export default function ForecastPage() {
  const [airport, setAirport] = useState(AIRPORT_CODES[0]);
  const [area, setArea] = useState("SECURITY_TSA");
  const [model, setModel] = useState("prophet");
  const [horizon, setHorizon] = useState(60);
  const [models, setModels] = useState<
    { name: string; label: string; default: boolean; horizon_max_min: number }[]
  >([]);
  const [points, setPoints] = useState<ForecastPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Load available models once
  useEffect(() => {
    async function loadModels() {
      try {
        const res = await api.getModels();
        setModels(res.models);
        const defaultModel = res.models.find((m) => m.default);
        if (defaultModel) setModel(defaultModel.name);
      } catch {
        // fallback to default
      }
    }
    loadModels();
  }, []);

  // Load forecast data
  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const res = await api.getForecast(airport, horizon, area, model);
        if (cancelled) return;
        setPoints(res.points);
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
  }, [airport, area, model, horizon]);

  const breachPoint = points.find(
    (p) => p.pred_wait_min >= 10
  );

  const chartData = points.map((p) => ({
    horizon: p.horizon_min,
    predicted: p.pred_wait_min,
    lower: p.lower_min,
    upper: p.upper_min,
    throughput: p.pred_throughput,
    time: p.target_ts,
  }));

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
      {/* Header + Controls */}
      <div className="flex flex-col gap-4">
        <h1 className="text-2xl font-bold">Forecast</h1>
        <div className="flex flex-wrap items-center gap-4">
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted-foreground uppercase tracking-wider">
              Airport
            </span>
            <Select value={airport} onValueChange={(v) => v && setAirport(v)}>
              <SelectTrigger className="w-32">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {AIRPORT_CODES.map((code) => (
                  <SelectItem key={code} value={code}>
                    {code}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-xs text-muted-foreground uppercase tracking-wider">
              Area
            </span>
            <Select value={area} onValueChange={(v) => v && setArea(v)}>
              <SelectTrigger className="w-44">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {AREA_KEYS.map((key) => (
                  <SelectItem key={key} value={key}>
                    {AREA_LABELS[key]}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-xs text-muted-foreground uppercase tracking-wider">
              Model
            </span>
            <Select value={model} onValueChange={(v) => v && setModel(v)}>
              <SelectTrigger className="w-36">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {models.map((m) => (
                  <SelectItem key={m.name} value={m.name}>
                    {m.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="flex items-center gap-3 min-w-[200px]">
            <span className="text-xs text-muted-foreground uppercase tracking-wider whitespace-nowrap">
              Horizon
            </span>
            <Slider
              value={[horizon]}
              onValueChange={(v) => setHorizon(Array.isArray(v) ? v[0] : v)}
              min={15}
              max={180}
              step={15}
              className="w-32"
            />
            <span className="text-sm font-mono w-12 text-right">
              {horizon}m
            </span>
          </div>
        </div>
      </div>

      {loading ? (
        <div className="text-muted-foreground py-20 text-center">
          Loading...
        </div>
      ) : (
        <>
          {/* Breach Forecast Callout */}
          {breachPoint && (
            <Card className="border-red-500/50 bg-red-500/5">
              <CardContent className="flex items-center gap-3 py-4">
                <AlertTriangle className="h-6 w-6 text-red-500 shrink-0" />
                <div>
                  <div className="font-semibold text-red-500">
                    SLA Breach Predicted
                  </div>
                  <p className="text-sm text-muted-foreground">
                    Wait time expected to exceed 10 min SLA at +
                    {breachPoint.horizon_min} min (predicted{" "}
                    {breachPoint.pred_wait_min.toFixed(1)} min)
                  </p>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Main Forecast Chart with Confidence Band */}
          <Card>
            <CardHeader>
              <CardTitle>
                Wait Time Forecast{" "}
                <span className="text-sm font-normal text-muted-foreground">
                  ({airport} &middot; {AREA_LABELS[area] || area} &middot;{" "}
                  {models.find((m) => m.name === model)?.label || model})
                </span>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-80">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={chartData}>
                    <CartesianGrid
                      strokeDasharray="3 3"
                      stroke="#2D3139"
                    />
                    <XAxis
                      dataKey="horizon"
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
                      formatter={(v, name) => {
                        const labels: Record<string, string> = {
                          predicted: "Predicted",
                          upper: "Upper Bound",
                          lower: "Lower Bound",
                        };
                        return [
                          `${Number(v).toFixed(1)} min`,
                          labels[String(name)] || String(name),
                        ];
                      }}
                    />
                    <ReferenceLine
                      y={10}
                      stroke="#F85149"
                      strokeDasharray="4 4"
                      label={{
                        value: "SLA (10 min)",
                        fill: "#F85149",
                        fontSize: 11,
                      }}
                    />
                    {/* Confidence band: upper area */}
                    <Area
                      type="monotone"
                      dataKey="upper"
                      stroke="none"
                      fill="#0080FF"
                      fillOpacity={0.1}
                    />
                    {/* Confidence band: lower area (subtracts to create band) */}
                    <Area
                      type="monotone"
                      dataKey="lower"
                      stroke="none"
                      fill="#0D1117"
                      fillOpacity={0.8}
                    />
                    {/* Predicted line */}
                    <Area
                      type="monotone"
                      dataKey="predicted"
                      stroke="#0080FF"
                      strokeWidth={2}
                      fill="none"
                      dot={false}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>

          {/* Throughput Bar Chart */}
          {chartData.some((d) => d.throughput != null) && (
            <Card>
              <CardHeader>
                <CardTitle>Predicted Throughput</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={chartData}>
                      <CartesianGrid
                        strokeDasharray="3 3"
                        stroke="#2D3139"
                      />
                      <XAxis
                        dataKey="horizon"
                        tick={{ fill: "#8B949E", fontSize: 12 }}
                        tickFormatter={(v: number) => `+${v}m`}
                      />
                      <YAxis
                        tick={{ fill: "#8B949E", fontSize: 12 }}
                        tickFormatter={(v: number) => `${v}`}
                      />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: "#161B22",
                          border: "1px solid #30363D",
                          borderRadius: 8,
                        }}
                        labelFormatter={(v) => `+${v} min`}
                        formatter={(v) => [
                          `${Number(v).toFixed(0)} pax`,
                          "Throughput",
                        ]}
                      />
                      <Bar
                        dataKey="throughput"
                        fill="#58A6FF"
                        radius={[4, 4, 0, 0]}
                      />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Data Table */}
          <Card>
            <CardHeader>
              <CardTitle>Forecast Data Points</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border text-muted-foreground text-xs uppercase tracking-wider">
                      <th className="text-left py-3 px-2">Horizon</th>
                      <th className="text-left py-3 px-2">Target Time</th>
                      <th className="text-right py-3 px-2">Predicted Wait</th>
                      <th className="text-right py-3 px-2">Lower</th>
                      <th className="text-right py-3 px-2">Upper</th>
                      <th className="text-right py-3 px-2">Throughput</th>
                      <th className="text-center py-3 px-2">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {points.map((p, i) => (
                      <tr
                        key={i}
                        className="border-b border-border/50 hover:bg-muted/30"
                      >
                        <td className="py-2.5 px-2 font-mono">
                          +{p.horizon_min}m
                        </td>
                        <td className="py-2.5 px-2 text-muted-foreground">
                          {new Date(p.target_ts).toLocaleTimeString([], {
                            hour: "2-digit",
                            minute: "2-digit",
                          })}
                        </td>
                        <td className="py-2.5 px-2 text-right font-mono font-semibold">
                          {p.pred_wait_min.toFixed(1)} min
                        </td>
                        <td className="py-2.5 px-2 text-right text-muted-foreground font-mono">
                          {p.lower_min != null
                            ? `${p.lower_min.toFixed(1)}`
                            : "—"}
                        </td>
                        <td className="py-2.5 px-2 text-right text-muted-foreground font-mono">
                          {p.upper_min != null
                            ? `${p.upper_min.toFixed(1)}`
                            : "—"}
                        </td>
                        <td className="py-2.5 px-2 text-right font-mono">
                          {p.pred_throughput != null
                            ? p.pred_throughput.toFixed(0)
                            : "—"}
                        </td>
                        <td className="py-2.5 px-2 text-center">
                          <StatusBadge
                            status={
                              p.pred_wait_min >= 10
                                ? "BREACH"
                                : p.pred_wait_min >= 8
                                  ? "WARNING"
                                  : "OK"
                            }
                          />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
