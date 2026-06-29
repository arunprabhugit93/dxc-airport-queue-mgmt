"use client";

import { useState, useEffect, useMemo } from "react";
import { useClock } from "@/components/clock-context";
import { api, AIRPORT_CODES, SEVERITY_COLORS, type AnomalyEvent } from "@/lib/api";
import { MetricCard } from "@/components/metric-card";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from "@/components/ui/select";
import { Slider } from "@/components/ui/slider";
import { AlertTriangle, ArrowUpDown, Clock, Shield } from "lucide-react";
import {
  ResponsiveContainer,
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  BarChart,
  Bar,
  Cell,
} from "recharts";

const SEVERITIES = ["ALL", "LOW", "MEDIUM", "HIGH"];
const TYPES = ["ALL", "spike", "drift", "flatline", "threshold_breach", "statistical_outlier"];

export default function AnomaliesPage() {
  const { demoNow } = useClock();
  const [airport, setAirport] = useState("All");
  const [hours, setHours] = useState(24);
  const [severityFilter, setSeverityFilter] = useState("ALL");
  const [typeFilter, setTypeFilter] = useState("ALL");
  const [events, setEvents] = useState<AnomalyEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sortField, setSortField] = useState<"detected_at" | "score">("detected_at");
  const [sortAsc, setSortAsc] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const data = await api.getAnomalies(airport === "All" ? undefined : airport, hours);
        if (!cancelled) setEvents(data.events);
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : "Failed to load anomalies");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, [demoNow, airport, hours]);

  const filtered = useMemo(() => {
    return events.filter((e) => {
      if (severityFilter !== "ALL" && e.severity !== severityFilter) return false;
      if (typeFilter !== "ALL" && e.anomaly_type !== typeFilter) return false;
      return true;
    });
  }, [events, severityFilter, typeFilter]);

  const highIncidents = filtered.filter((e) => e.severity === "HIGH");

  const sorted = useMemo(() => {
    return [...filtered].sort((a, b) => {
      const va = sortField === "detected_at" ? new Date(a.detected_at).getTime() : a.score;
      const vb = sortField === "detected_at" ? new Date(b.detected_at).getTime() : b.score;
      return sortAsc ? va - vb : vb - va;
    });
  }, [filtered, sortField, sortAsc]);

  // Chart data
  const airportList = [...new Set(events.map((e) => e.airport_code))];

  const scatterData = filtered.map((e) => ({
    x: new Date(e.detected_at).getTime(),
    y: airportList.indexOf(e.airport_code),
    airport: e.airport_code,
    score: e.score,
    severity: e.severity,
    type: e.anomaly_type,
    description: e.description,
  }));

  const typeBreakdown = useMemo(() => {
    const counts: Record<string, number> = {};
    filtered.forEach((e) => { counts[e.anomaly_type] = (counts[e.anomaly_type] || 0) + 1; });
    return Object.entries(counts).map(([name, count]) => ({ name, count }));
  }, [filtered]);

  const detectorBreakdown = useMemo(() => {
    const counts: Record<string, number> = {};
    filtered.forEach((e) => { counts[e.detector] = (counts[e.detector] || 0) + 1; });
    return Object.entries(counts).map(([name, count]) => ({ name, count }));
  }, [filtered]);

  const crossAirport = useMemo(() => {
    const counts: Record<string, number> = {};
    filtered.forEach((e) => { counts[e.airport_code] = (counts[e.airport_code] || 0) + 1; });
    return Object.entries(counts).map(([airport, count]) => ({ airport, count }));
  }, [filtered]);

  function toggleSort(field: "detected_at" | "score") {
    if (sortField === field) {
      setSortAsc(!sortAsc);
    } else {
      setSortField(field);
      setSortAsc(false);
    }
  }

  if (error) {
    return (
      <div className="p-6">
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 text-red-400">
          <AlertTriangle className="inline h-4 w-4 mr-2" />
          {error}
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center gap-2 mb-2">
        <AlertTriangle className="h-6 w-6 text-red-500" />
        <h1 className="text-2xl font-bold text-foreground">Anomaly & Incident Intelligence</h1>
      </div>

      {/* Controls */}
      <div className="flex flex-wrap items-end gap-4 bg-card border border-border rounded-lg p-4">
        <div className="flex flex-col gap-1">
          <label className="text-xs text-muted-foreground uppercase tracking-wider">Airport</label>
          <Select value={airport} onValueChange={(v) => v && setAirport(v)}>
            <SelectTrigger className="w-[130px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="All">All Airports</SelectItem>
              {AIRPORT_CODES.map((c) => (
                <SelectItem key={c} value={c}>{c}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="flex flex-col gap-1 min-w-[200px]">
          <label className="text-xs text-muted-foreground uppercase tracking-wider">
            Hours: {hours}
          </label>
          <Slider
            min={1}
            max={720}
            value={[hours]}
            onValueChange={(v) => setHours(Array.isArray(v) ? v[0] : v)}
          />
        </div>

        <div className="flex flex-col gap-1">
          <label className="text-xs text-muted-foreground uppercase tracking-wider">Severity</label>
          <Select value={severityFilter} onValueChange={(v) => v && setSeverityFilter(v)}>
            <SelectTrigger className="w-[120px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {SEVERITIES.map((s) => (
                <SelectItem key={s} value={s}>{s}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="flex flex-col gap-1">
          <label className="text-xs text-muted-foreground uppercase tracking-wider">Type</label>
          <Select value={typeFilter} onValueChange={(v) => v && setTypeFilter(v)}>
            <SelectTrigger className="w-[180px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {TYPES.map((t) => (
                <SelectItem key={t} value={t}>{t === "ALL" ? "All Types" : t.replace(/_/g, " ")}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="text-sm text-muted-foreground ml-auto">
          {loading ? "Loading..." : `${filtered.length} events`}
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-64 text-muted-foreground">
          <div className="animate-pulse">Loading anomaly data...</div>
        </div>
      ) : (
        <>
          {/* Active HIGH-severity incidents */}
          {highIncidents.length > 0 && (
            <div className="space-y-3">
              <h2 className="text-lg font-semibold text-foreground flex items-center gap-2">
                <Shield className="h-5 w-5 text-red-500" />
                Active HIGH-Severity Incidents ({highIncidents.length})
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {highIncidents.slice(0, 6).map((inc) => (
                  <Card key={inc.event_id} className="border-l-4 border-l-red-500">
                    <CardContent className="pt-4">
                      <div className="flex items-start justify-between mb-2">
                        <Badge variant="destructive">{inc.anomaly_type.replace(/_/g, " ")}</Badge>
                        <span className="text-xs text-muted-foreground">
                          {inc.airport_code} &middot; Score: {inc.score.toFixed(2)}
                        </span>
                      </div>
                      <p className="text-sm text-foreground mb-1">
                        {inc.description || `${inc.metric}: observed ${inc.observed_value.toFixed(1)} vs expected ${inc.expected_value?.toFixed(1) ?? "N/A"}`}
                      </p>
                      <p className="text-xs text-muted-foreground flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        {new Date(inc.detected_at).toLocaleString()}
                      </p>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </div>
          )}

          {/* Anomaly Timeline Scatter */}
          <Card>
            <CardHeader>
              <CardTitle>Anomaly Timeline</CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={350}>
                <ScatterChart margin={{ top: 20, right: 30, bottom: 20, left: 60 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#2D3139" />
                  <XAxis
                    dataKey="x"
                    type="number"
                    domain={["dataMin", "dataMax"]}
                    tickFormatter={(v) => new Date(v).toLocaleDateString()}
                    tick={{ fill: "#8B949E", fontSize: 12 }}
                    stroke="#2D3139"
                  />
                  <YAxis
                    dataKey="y"
                    type="number"
                    domain={[0, Math.max(airportList.length - 1, 0)]}
                    tickFormatter={(v) => airportList[v] || ""}
                    tick={{ fill: "#8B949E", fontSize: 12 }}
                    stroke="#2D3139"
                  />
                  <Tooltip
                    content={({ payload }) => {
                      if (!payload?.[0]) return null;
                      const d = payload[0].payload;
                      return (
                        <div className="bg-card border border-border rounded-lg p-3 shadow-lg text-sm">
                          <div className="font-semibold">{d.airport} &middot; {d.type}</div>
                          <div>Severity: {d.severity}</div>
                          <div>Score: {d.score.toFixed(2)}</div>
                          <div className="text-xs text-muted-foreground">{new Date(d.x).toLocaleString()}</div>
                        </div>
                      );
                    }}
                  />
                  <Scatter data={scatterData} isAnimationActive={false}>
                    {scatterData.map((entry, i) => (
                      <Cell
                        key={i}
                        fill={SEVERITY_COLORS[entry.severity] || "#636B74"}
                        r={Math.max(4, Math.min(entry.score * 4, 12))}
                      />
                    ))}
                  </Scatter>
                </ScatterChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          {/* Type + Detector Breakdown Side by Side */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle>Type Breakdown</CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={350}>
                  <BarChart data={typeBreakdown} margin={{ top: 10, right: 20, bottom: 40, left: 20 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#2D3139" />
                    <XAxis
                      dataKey="name"
                      tick={{ fill: "#8B949E", fontSize: 11 }}
                      angle={-30}
                      textAnchor="end"
                      stroke="#2D3139"
                    />
                    <YAxis tick={{ fill: "#8B949E", fontSize: 12 }} stroke="#2D3139" />
                    <Tooltip
                      contentStyle={{ backgroundColor: "var(--card)", border: "1px solid var(--border)", borderRadius: 8 }}
                      labelStyle={{ color: "var(--foreground)" }}
                    />
                    <Bar dataKey="count" fill="#0080FF" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Detector Breakdown</CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={350}>
                  <BarChart data={detectorBreakdown} margin={{ top: 10, right: 20, bottom: 40, left: 20 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#2D3139" />
                    <XAxis
                      dataKey="name"
                      tick={{ fill: "#8B949E", fontSize: 11 }}
                      angle={-30}
                      textAnchor="end"
                      stroke="#2D3139"
                    />
                    <YAxis tick={{ fill: "#8B949E", fontSize: 12 }} stroke="#2D3139" />
                    <Tooltip
                      contentStyle={{ backgroundColor: "var(--card)", border: "1px solid var(--border)", borderRadius: 8 }}
                      labelStyle={{ color: "var(--foreground)" }}
                    />
                    <Bar dataKey="count" fill="#58A6FF" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </div>

          {/* Cross-airport comparison */}
          <Card>
            <CardHeader>
              <CardTitle>Cross-Airport Comparison</CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={350}>
                <BarChart data={crossAirport} margin={{ top: 10, right: 20, bottom: 20, left: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#2D3139" />
                  <XAxis dataKey="airport" tick={{ fill: "#8B949E", fontSize: 12 }} stroke="#2D3139" />
                  <YAxis tick={{ fill: "#8B949E", fontSize: 12 }} stroke="#2D3139" />
                  <Tooltip
                    contentStyle={{ backgroundColor: "var(--card)", border: "1px solid var(--border)", borderRadius: 8 }}
                    labelStyle={{ color: "var(--foreground)" }}
                  />
                  <Bar dataKey="count" fill="#D29922" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          {/* Event Detail Table */}
          <Card>
            <CardHeader>
              <CardTitle>Event Details</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border text-left">
                      <th className="py-2 px-3 text-muted-foreground font-medium">
                        <button onClick={() => toggleSort("detected_at")} className="flex items-center gap-1 hover:text-foreground">
                          Detected At <ArrowUpDown className="h-3 w-3" />
                        </button>
                      </th>
                      <th className="py-2 px-3 text-muted-foreground font-medium">Airport</th>
                      <th className="py-2 px-3 text-muted-foreground font-medium">Type</th>
                      <th className="py-2 px-3 text-muted-foreground font-medium">Severity</th>
                      <th className="py-2 px-3 text-muted-foreground font-medium">
                        <button onClick={() => toggleSort("score")} className="flex items-center gap-1 hover:text-foreground">
                          Score <ArrowUpDown className="h-3 w-3" />
                        </button>
                      </th>
                      <th className="py-2 px-3 text-muted-foreground font-medium">Metric</th>
                      <th className="py-2 px-3 text-muted-foreground font-medium">Observed</th>
                      <th className="py-2 px-3 text-muted-foreground font-medium">Expected</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sorted.slice(0, 50).map((e) => (
                      <tr key={e.event_id} className="border-b border-border/50 hover:bg-muted/30">
                        <td className="py-2 px-3 text-xs">{new Date(e.detected_at).toLocaleString()}</td>
                        <td className="py-2 px-3 font-mono">{e.airport_code}</td>
                        <td className="py-2 px-3">{e.anomaly_type.replace(/_/g, " ")}</td>
                        <td className="py-2 px-3">
                          <span
                            className="px-2 py-0.5 rounded text-xs font-semibold"
                            style={{ backgroundColor: SEVERITY_COLORS[e.severity] + "20", color: SEVERITY_COLORS[e.severity] }}
                          >
                            {e.severity}
                          </span>
                        </td>
                        <td className="py-2 px-3 font-mono">{e.score.toFixed(2)}</td>
                        <td className="py-2 px-3">{e.metric}</td>
                        <td className="py-2 px-3 font-mono">{e.observed_value.toFixed(1)}</td>
                        <td className="py-2 px-3 font-mono">{e.expected_value?.toFixed(1) ?? "N/A"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {sorted.length > 50 && (
                  <p className="text-xs text-muted-foreground mt-2 text-center">
                    Showing 50 of {sorted.length} events
                  </p>
                )}
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
