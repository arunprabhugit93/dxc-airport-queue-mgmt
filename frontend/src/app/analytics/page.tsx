"use client";

import { useState, useEffect, useMemo } from "react";
import { useClock } from "@/components/clock-context";
import { api, AIRPORT_CODES } from "@/lib/api";
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
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { BarChart3, Download, TrendingUp, AlertTriangle } from "lucide-react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  BarChart,
  Bar,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from "recharts";

interface TrendPoint {
  obs_date: string;
  avg_wait_min: number;
  total_pax: number;
  sla_breach_rate: number;
}

interface KpiData {
  kpis: Record<string, number | string>;
  trend: TrendPoint[];
}

export default function AnalyticsPage() {
  const { demoNow } = useClock();
  const [airport, setAirport] = useState("ALL");
  const [dateFrom, setDateFrom] = useState("2022-06-01");
  const [dateTo, setDateTo] = useState("2022-10-15");
  const [data, setData] = useState<KpiData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Per-airport data for rankings
  const [airportData, setAirportData] = useState<{ airport: string; avg_wait: number }[]>([]);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const result = await api.getKpis(dateFrom, dateTo, airport);
        if (!cancelled) {
          setData({ kpis: result.kpis, trend: result.trend });
        }

        // Load per-airport data for comparison when ALL
        if (airport === "ALL" && !cancelled) {
          try {
            const rankings = await Promise.all(
              AIRPORT_CODES.map(async (code) => {
                const r = await api.getKpis(dateFrom, dateTo, code);
                return {
                  airport: code,
                  avg_wait: typeof r.kpis.avg_wait_min === "number" ? r.kpis.avg_wait_min : 0,
                };
              })
            );
            if (!cancelled) setAirportData(rankings);
          } catch {
            // Non-critical, skip rankings
          }
        } else {
          if (!cancelled) setAirportData([]);
        }
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : "Failed to load analytics");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, [demoNow, airport, dateFrom, dateTo]);

  const kpis = data?.kpis ?? {};
  const trend = data?.trend ?? [];

  const trendData = trend.map((t) => ({
    date: t.obs_date,
    avg_wait: t.avg_wait_min,
    total_pax: t.total_pax,
    sla_breach_rate: t.sla_breach_rate * 100,
  }));

  // Executive summary
  const summary = useMemo(() => {
    if (!data) return "";
    const avgWait = typeof kpis.avg_wait_min === "number" ? kpis.avg_wait_min : 0;
    const p95 = typeof kpis.p95_wait_min === "number" ? kpis.p95_wait_min : 0;
    const totalPax = typeof kpis.total_pax === "number" ? kpis.total_pax : 0;
    const breachRate = typeof kpis.sla_breach_rate === "number" ? (kpis.sla_breach_rate as number) * 100 : 0;
    const anomalies = typeof kpis.anomaly_count === "number" ? kpis.anomaly_count : 0;
    const busiest = kpis.busiest_airport || "N/A";

    const airportLabel = airport === "ALL" ? "across all airports" : `at ${airport}`;
    return `From ${dateFrom} to ${dateTo} ${airportLabel}, the average wait time was ${avgWait.toFixed(1)} minutes with a P95 of ${p95.toFixed(1)} minutes. A total of ${totalPax.toLocaleString()} passengers were processed with an SLA breach rate of ${breachRate.toFixed(1)}%. ${anomalies} anomalies were detected during this period. ${busiest !== "N/A" ? `The busiest airport was ${busiest}.` : ""}`;
  }, [data, kpis, airport, dateFrom, dateTo]);

  function downloadCSV() {
    const header = "Date,Avg Wait (min),Total Pax,SLA Breach Rate (%)\n";
    const rows = trend.map((t) =>
      `${t.obs_date},${t.avg_wait_min.toFixed(1)},${t.total_pax},${(t.sla_breach_rate * 100).toFixed(1)}`
    ).join("\n");
    const blob = new Blob([header + rows], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `analytics-${airport}-${dateFrom}-to-${dateTo}.csv`;
    a.click();
    URL.revokeObjectURL(url);
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
        <BarChart3 className="h-6 w-6 text-blue-500" />
        <h1 className="text-2xl font-bold text-foreground">Analytics & Reporting</h1>
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
              <SelectItem value="ALL">All Airports</SelectItem>
              {AIRPORT_CODES.map((c) => (
                <SelectItem key={c} value={c}>{c}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="flex flex-col gap-1">
          <label className="text-xs text-muted-foreground uppercase tracking-wider">From</label>
          <input
            type="date" min="2020-02-15" max="2022-10-15"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
            className="h-8 rounded-lg border border-input bg-transparent px-2.5 text-sm text-foreground outline-none focus:border-ring focus:ring-3 focus:ring-ring/50"
          />
        </div>

        <div className="flex flex-col gap-1">
          <label className="text-xs text-muted-foreground uppercase tracking-wider">To</label>
          <input
            type="date" min="2020-02-15" max="2022-10-15"
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
            className="h-8 rounded-lg border border-input bg-transparent px-2.5 text-sm text-foreground outline-none focus:border-ring focus:ring-3 focus:ring-ring/50"
          />
        </div>

        <Button variant="outline" size="sm" onClick={downloadCSV} disabled={trend.length === 0}>
          <Download className="h-4 w-4 mr-1" />
          Download CSV
        </Button>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-64 text-muted-foreground">
          <div className="animate-pulse">Loading analytics...</div>
        </div>
      ) : (
        <>
          {/* Executive Summary */}
          {summary && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <TrendingUp className="h-4 w-4" />
                  Executive Summary
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground leading-relaxed">{summary}</p>
              </CardContent>
            </Card>
          )}

          {/* KPI Cards */}
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
            <MetricCard
              label="Avg Wait"
              value={typeof kpis.avg_wait_min === "number" ? `${(kpis.avg_wait_min as number).toFixed(1)}m` : "N/A"}
              accentColor="#0080FF"
            />
            <MetricCard
              label="P95 Wait"
              value={typeof kpis.p95_wait_min === "number" ? `${(kpis.p95_wait_min as number).toFixed(1)}m` : "N/A"}
              accentColor="#58A6FF"
            />
            <MetricCard
              label="Total Pax"
              value={typeof kpis.total_pax === "number" ? (kpis.total_pax as number).toLocaleString() : "N/A"}
              accentColor="#2EA043"
            />
            <MetricCard
              label="SLA Breach Rate"
              value={typeof kpis.sla_breach_rate === "number" ? `${((kpis.sla_breach_rate as number) * 100).toFixed(1)}%` : "N/A"}
              accentColor={typeof kpis.sla_breach_rate === "number" && (kpis.sla_breach_rate as number) > 0.1 ? "#F85149" : "#2EA043"}
            />
            <MetricCard
              label="Anomaly Count"
              value={typeof kpis.anomaly_count === "number" ? kpis.anomaly_count : "N/A"}
              accentColor="#D29922"
            />
            <MetricCard
              label="Busiest"
              value={typeof kpis.busiest_airport === "string" ? (kpis.busiest_airport as string) : typeof kpis.busiest_hour === "number" ? `Hour ${kpis.busiest_hour}` : "N/A"}
              sublabel={typeof kpis.busiest_hour === "number" ? `Peak at ${kpis.busiest_hour}:00` : undefined}
              accentColor="#DB6D28"
            />
          </div>

          {/* Trend Charts in Tabs */}
          <Card>
            <CardContent className="pt-6">
              <Tabs defaultValue="wait">
                <TabsList>
                  <TabsTrigger value="wait">Wait Time</TabsTrigger>
                  <TabsTrigger value="volume">Passenger Volume</TabsTrigger>
                  <TabsTrigger value="sla">SLA Breach Rate</TabsTrigger>
                </TabsList>

                <TabsContent value="wait" className="mt-4">
                  <ResponsiveContainer width="100%" height={350}>
                    <LineChart data={trendData} margin={{ top: 10, right: 20, bottom: 20, left: 20 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#2D3139" />
                      <XAxis dataKey="date" tick={{ fill: "#8B949E", fontSize: 12 }} stroke="#2D3139" />
                      <YAxis tick={{ fill: "#8B949E", fontSize: 12 }} stroke="#2D3139" />
                      <Tooltip
                        contentStyle={{ backgroundColor: "var(--card)", border: "1px solid var(--border)", borderRadius: 8 }}
                        labelStyle={{ color: "var(--foreground)" }}
                      />
                      <Legend />
                      <Line
                        type="monotone"
                        dataKey="avg_wait"
                        stroke="#0080FF"
                        strokeWidth={2}
                        dot={{ r: 3 }}
                        name="Avg Wait (min)"
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </TabsContent>

                <TabsContent value="volume" className="mt-4">
                  <ResponsiveContainer width="100%" height={350}>
                    <BarChart data={trendData} margin={{ top: 10, right: 20, bottom: 20, left: 20 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#2D3139" />
                      <XAxis dataKey="date" tick={{ fill: "#8B949E", fontSize: 12 }} stroke="#2D3139" />
                      <YAxis tick={{ fill: "#8B949E", fontSize: 12 }} stroke="#2D3139" />
                      <Tooltip
                        contentStyle={{ backgroundColor: "var(--card)", border: "1px solid var(--border)", borderRadius: 8 }}
                        labelStyle={{ color: "var(--foreground)" }}
                      />
                      <Legend />
                      <Bar dataKey="total_pax" fill="#2EA043" radius={[4, 4, 0, 0]} name="Total Passengers" />
                    </BarChart>
                  </ResponsiveContainer>
                </TabsContent>

                <TabsContent value="sla" className="mt-4">
                  <ResponsiveContainer width="100%" height={350}>
                    <AreaChart data={trendData} margin={{ top: 10, right: 20, bottom: 20, left: 20 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#2D3139" />
                      <XAxis dataKey="date" tick={{ fill: "#8B949E", fontSize: 12 }} stroke="#2D3139" />
                      <YAxis tick={{ fill: "#8B949E", fontSize: 12 }} stroke="#2D3139" unit="%" />
                      <Tooltip
                        contentStyle={{ backgroundColor: "var(--card)", border: "1px solid var(--border)", borderRadius: 8 }}
                        labelStyle={{ color: "var(--foreground)" }}
                        formatter={(value: any) => [`${value.toFixed(1)}%`, "SLA Breach Rate"]}
                      />
                      <Legend />
                      <Area
                        type="monotone"
                        dataKey="sla_breach_rate"
                        stroke="#F85149"
                        fill="#F85149"
                        fillOpacity={0.15}
                        strokeWidth={2}
                        name="SLA Breach Rate (%)"
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </TabsContent>
              </Tabs>
            </CardContent>
          </Card>

          {/* Airport Ranking (when ALL selected) */}
          {airport === "ALL" && airportData.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Airport Ranking by Average Wait</CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={350}>
                  <BarChart
                    data={[...airportData].sort((a, b) => a.avg_wait - b.avg_wait)}
                    margin={{ top: 10, right: 20, bottom: 20, left: 20 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="#2D3139" />
                    <XAxis dataKey="airport" tick={{ fill: "#8B949E", fontSize: 12 }} stroke="#2D3139" />
                    <YAxis tick={{ fill: "#8B949E", fontSize: 12 }} stroke="#2D3139" label={{ value: "Avg Wait (min)", angle: -90, position: "insideLeft", fill: "#8B949E" }} />
                    <Tooltip
                      contentStyle={{ backgroundColor: "var(--card)", border: "1px solid var(--border)", borderRadius: 8 }}
                      labelStyle={{ color: "var(--foreground)" }}
                      formatter={(value: any) => [`${value.toFixed(1)} min`, "Avg Wait"]}
                    />
                    <Bar dataKey="avg_wait" fill="#0080FF" radius={[4, 4, 0, 0]} name="Avg Wait (min)" />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
