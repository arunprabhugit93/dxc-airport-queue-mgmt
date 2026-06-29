"use client";

import { useEffect, useState } from "react";
import { useClock } from "@/components/clock-context";
import { api, AIRPORT_CODES, AREA_LABELS, SLA_COLORS } from "@/lib/api";
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
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  Cell,
} from "recharts";
import { AlertTriangle, Clock, Layers, Users, TrendingUp } from "lucide-react";
import type { HeatmapCell } from "@/lib/api";
import { useAutoRefresh } from "@/lib/use-auto-refresh";

function heatColor(val: number): string {
  if (val <= 0) return "bg-gray-800";
  if (val < 5) return "bg-green-900";
  if (val < 8) return "bg-green-700";
  if (val < 10) return "bg-yellow-700";
  if (val < 15) return "bg-orange-700";
  if (val < 30) return "bg-red-700";
  return "bg-red-900";
}

const DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

interface AreaQueue {
  airport_code: string;
  area_type: string;
  queue_length: number;
  wait_min: number;
  staff_on_duty: number;
  sla_status: string;
}

interface CapacityArea {
  area_type: string;
  current_throughput: number;
  max_capacity: number;
  utilization_pct: number;
  headroom_pax: number;
  status: string;
}

function vsTypicalLabel(current: number, typical: number | null): { text: string; color: string } | null {
  if (typical === null || typical === 0) return null;
  const pct = ((current - typical) / typical) * 100;
  if (Math.abs(pct) < 5) return null;
  if (pct > 0) return { text: `+${pct.toFixed(0)}% vs typical`, color: pct > 30 ? "#F85149" : "#D29922" };
  return { text: `${pct.toFixed(0)}% vs typical`, color: "#2EA043" };
}

const HEATMAP_AREA_OPTIONS = [
  { value: "SECURITY_TSA", label: "Security (TSA)" },
  { value: "SECURITY_PRECHECK", label: "PreCheck" },
  { value: "CHECKIN", label: "Check-in" },
  { value: "GATE", label: "Gate" },
  { value: "BAGGAGE", label: "Baggage" },
  { value: "IMMIGRATION", label: "Immigration" },
];

export default function QueuesPage() {
  const { demoNow } = useClock();
  const [airport, setAirport] = useState(AIRPORT_CODES[0]);
  const [heatmapArea, setHeatmapArea] = useState("SECURITY_TSA");
  const [refreshInterval, setRefreshInterval] = useState<number | null>(null);
  const refreshTick = useAutoRefresh(refreshInterval);

  const [queues, setQueues] = useState<AreaQueue[]>([]);
  const [heatmap, setHeatmap] = useState<HeatmapCell[]>([]);
  const [capacity, setCapacity] = useState<CapacityArea[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const [qRes, hRes, cRes] = await Promise.all([
          api.getAllAreaQueues(airport),
          api.getHeatmap(airport, heatmapArea),
          api.getCapacity(airport),
        ]);
        if (cancelled) return;
        setQueues(qRes.queues);
        setHeatmap(hRes.cells);
        setCapacity(cRes.areas);
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
  }, [demoNow, airport, heatmapArea, refreshTick]);

  // Current hour + day of week from demo clock
  const currentHour = demoNow ? parseInt(demoNow.slice(11, 13)) : null;
  const currentDow = demoNow
    ? ((new Date(demoNow).getDay() + 6) % 7)  // 0=Mon…6=Sun
    : null;

  const typicalWait: number | null = (() => {
    if (currentHour === null || currentDow === null) return null;
    const cell = heatmap.find(
      (c) => c.day_of_week === currentDow && c.hour === currentHour,
    );
    return cell ? cell.avg_wait_min : null;
  })();

  const barData = queues.map((q) => ({
    name: AREA_LABELS[q.area_type] || q.area_type,
    wait: q.wait_min,
    queue: q.queue_length,
    status: q.sla_status,
  }));

  // Heatmap grid: 7 days x 24 hours
  const heatGrid: number[][] = Array.from({ length: 7 }, () =>
    Array(24).fill(0),
  );
  heatmap.forEach((cell) => {
    if (
      cell.day_of_week >= 0 &&
      cell.day_of_week < 7 &&
      cell.hour >= 0 &&
      cell.hour < 24
    ) {
      heatGrid[cell.day_of_week][cell.hour] = cell.avg_wait_min;
    }
  });

  const breachAreas = queues.filter((q) => q.sla_status === "BREACH");
  const warnAreas = queues.filter((q) => q.sla_status === "WARNING");
  const worstArea = queues.length
    ? queues.slice().sort((a, b) => b.wait_min - a.wait_min)[0]
    : null;

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
      <div className="flex items-center justify-between flex-wrap gap-3">
        <h1 className="text-2xl font-bold">Queue Intelligence</h1>
        <div className="flex items-center gap-3 flex-wrap">
          {/* Auto-refresh */}
          <div className="flex rounded-md border border-border overflow-hidden text-xs">
            {[{ label: "Off", value: null }, { label: "30s", value: 30 }, { label: "60s", value: 60 }].map((opt) => (
              <button
                key={String(opt.value)}
                onClick={() => setRefreshInterval(opt.value as number | null)}
                className={`px-2.5 py-1 transition-colors ${refreshInterval === opt.value ? "bg-blue-600 text-white" : "bg-card text-muted-foreground hover:text-foreground hover:bg-muted"}`}
              >
                {opt.label}
              </button>
            ))}
          </div>
          <Select value={airport} onValueChange={(v) => v && setAirport(v)}>
            <SelectTrigger className="w-36">
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
      </div>

      {loading ? (
        <div className="text-muted-foreground py-20 text-center">Loading…</div>
      ) : (
        <>
          {/* Critical Zone Spotlight */}
          {worstArea && (breachAreas.length > 0 || warnAreas.length > 0) && (
            <Card
              className={`border ${
                breachAreas.length > 0
                  ? "border-red-500/50 bg-red-500/5"
                  : "border-yellow-500/50 bg-yellow-500/5"
              }`}
            >
              <CardContent className="flex items-start gap-4 py-5">
                <AlertTriangle
                  className={`h-5 w-5 mt-0.5 shrink-0 ${
                    breachAreas.length > 0 ? "text-red-500" : "text-yellow-500"
                  }`}
                />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-bold">
                      {AREA_LABELS[worstArea.area_type] || worstArea.area_type}
                    </span>
                    <StatusBadge status={worstArea.sla_status} />
                  </div>
                  <p className="text-sm text-muted-foreground">
                    Current wait{" "}
                    <span className="font-semibold text-foreground">
                      {worstArea.wait_min.toFixed(1)} min
                    </span>
                    {typicalWait !== null &&
                      worstArea.area_type === heatmapArea && (
                        <span>
                          {" "}
                          —{" "}
                          {(() => {
                            const ctx = vsTypicalLabel(
                              worstArea.wait_min,
                              typicalWait,
                            );
                            if (!ctx) return `typical for this hour is ${typicalWait.toFixed(1)} min`;
                            return (
                              <span style={{ color: ctx.color }}>
                                {ctx.text}
                              </span>
                            );
                          })()}
                        </span>
                      )}
                    {". "}
                    Queue depth{" "}
                    <span className="font-semibold text-foreground">
                      {worstArea.queue_length} pax
                    </span>{" "}
                    with{" "}
                    <span className="font-semibold text-foreground">
                      {worstArea.staff_on_duty} staff
                    </span>{" "}
                    on duty.
                    {breachAreas.length > 1 &&
                      ` ${breachAreas.length - 1} other area${breachAreas.length - 1 > 1 ? "s are" : " is"} also breaching SLA.`}
                  </p>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Area Queue Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {queues.map((q) => {
              const ctx =
                q.area_type === heatmapArea
                  ? vsTypicalLabel(q.wait_min, typicalWait)
                  : null;
              return (
                <Card key={q.area_type}>
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-base">
                        {AREA_LABELS[q.area_type] || q.area_type}
                      </CardTitle>
                      <StatusBadge status={q.sla_status} />
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-3 gap-3 text-sm">
                      <div>
                        <div className="text-xs text-muted-foreground flex items-center gap-1">
                          <Clock className="h-3 w-3" />
                          Wait
                        </div>
                        <div
                          className="font-bold text-xl leading-tight"
                          style={{
                            color:
                              q.sla_status === "BREACH"
                                ? SLA_COLORS.BREACH
                                : q.sla_status === "WARNING"
                                  ? SLA_COLORS.WARNING
                                  : undefined,
                          }}
                        >
                          {q.wait_min.toFixed(1)}
                          <span className="text-xs font-normal text-muted-foreground ml-0.5">
                            m
                          </span>
                        </div>
                        {ctx && (
                          <div
                            className="text-[10px] mt-0.5 font-medium"
                            style={{ color: ctx.color }}
                          >
                            {ctx.text}
                          </div>
                        )}
                        {typicalWait !== null &&
                          q.area_type === heatmapArea &&
                          !ctx && (
                            <div className="text-[10px] mt-0.5 text-muted-foreground">
                              typical: {typicalWait.toFixed(1)}m
                            </div>
                          )}
                      </div>
                      <div>
                        <div className="text-xs text-muted-foreground flex items-center gap-1">
                          <Layers className="h-3 w-3" />
                          Depth
                        </div>
                        <div className="font-bold text-xl leading-tight">
                          {q.queue_length}
                        </div>
                        <div className="text-[10px] text-muted-foreground mt-0.5">
                          pax in queue
                        </div>
                      </div>
                      <div>
                        <div className="text-xs text-muted-foreground flex items-center gap-1">
                          <Users className="h-3 w-3" />
                          Staff
                        </div>
                        <div className="font-bold text-xl leading-tight">
                          {q.staff_on_duty}
                        </div>
                        <div className="text-[10px] text-muted-foreground mt-0.5">
                          on duty
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>

          {/* Area Comparison Chart with SLA line */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Wait Time by Area</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={barData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#2D3139" />
                    <XAxis
                      dataKey="name"
                      tick={{ fill: "#8B949E", fontSize: 12 }}
                      angle={-20}
                      textAnchor="end"
                      height={60}
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
                      formatter={(v, name) => [
                        name === "wait"
                          ? `${Number(v).toFixed(1)} min`
                          : `${v} pax`,
                        name === "wait" ? "Wait Time" : "Queue Depth",
                      ]}
                    />
                    <ReferenceLine
                      y={10}
                      stroke="#F85149"
                      strokeDasharray="4 4"
                      label={{ value: "SLA 10m", fill: "#F85149", fontSize: 11 }}
                    />
                    <Bar dataKey="wait" radius={[4, 4, 0, 0]} name="wait">
                      {barData.map((entry, index) => (
                        <Cell
                          key={index}
                          fill={
                            entry.status === "BREACH"
                              ? "#F85149"
                              : entry.status === "WARNING"
                                ? "#D29922"
                                : "#0080FF"
                          }
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>

          {/* Heatmap */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between flex-wrap gap-2">
                <div>
                  <CardTitle className="text-base flex items-center gap-2">
                    <TrendingUp className="h-4 w-4 text-muted-foreground" />
                    Historical Wait Pattern
                  </CardTitle>
                  <p className="text-xs text-muted-foreground mt-1">
                    30-day average wait by hour — use this to predict busy
                    periods and plan staffing in advance.
                  </p>
                </div>
                <Select
                  value={heatmapArea}
                  onValueChange={(v) => v && setHeatmapArea(v)}
                >
                  <SelectTrigger className="w-44 h-8 text-xs">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {HEATMAP_AREA_OPTIONS.map((o) => (
                      <SelectItem key={o.value} value={o.value}>
                        {o.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <div className="min-w-[700px]">
                  <div className="flex ml-12 mb-1">
                    {Array.from({ length: 24 }, (_, h) => (
                      <div
                        key={h}
                        className={`flex-1 text-center text-[10px] ${h === currentHour ? "text-blue-400 font-bold" : "text-muted-foreground"}`}
                      >
                        {h}
                      </div>
                    ))}
                  </div>
                  {heatGrid.map((row, dayIdx) => (
                    <div key={dayIdx} className="flex items-center gap-1 mb-1">
                      <div className="w-10 text-xs text-muted-foreground text-right pr-2">
                        {DAY_NAMES[dayIdx]}
                      </div>
                      <div className="flex flex-1 gap-0.5">
                        {row.map((val, hourIdx) => {
                          const isCurrent =
                            hourIdx === currentHour &&
                            dayIdx === currentDow;
                          return (
                            <div
                              key={hourIdx}
                              className={`flex-1 h-6 rounded-sm ${heatColor(val)} cursor-default ${isCurrent ? "ring-2 ring-blue-400" : ""}`}
                              title={`${DAY_NAMES[dayIdx]} ${hourIdx}:00 — avg ${val.toFixed(1)} min${isCurrent ? " ← NOW" : ""}`}
                            />
                          );
                        })}
                      </div>
                    </div>
                  ))}
                  <div className="flex items-center gap-2 mt-4 ml-12 text-xs text-muted-foreground">
                    <span>Low (0–5m)</span>
                    <div className="flex gap-0.5">
                      <div className="w-6 h-3 rounded-sm bg-green-900" />
                      <div className="w-6 h-3 rounded-sm bg-green-700" />
                      <div className="w-6 h-3 rounded-sm bg-yellow-700" />
                      <div className="w-6 h-3 rounded-sm bg-orange-700" />
                      <div className="w-6 h-3 rounded-sm bg-red-700" />
                      <div className="w-6 h-3 rounded-sm bg-red-900" />
                    </div>
                    <span>High (30m+)</span>
                    <span className="ml-4 flex items-center gap-1">
                      <span className="w-3 h-3 rounded-sm inline-block ring-2 ring-blue-400 bg-gray-700" />
                      Current time
                    </span>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Capacity Utilization */}
          <Card>
            <CardHeader>
              <div>
                <CardTitle className="text-base">Capacity Utilization</CardTitle>
                <p className="text-xs text-muted-foreground mt-1">
                  How full each area is relative to its theoretical maximum —
                  above 90% is critical.
                </p>
              </div>
            </CardHeader>
            <CardContent>
              <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={capacity.map((c) => ({
                      name: AREA_LABELS[c.area_type] || c.area_type,
                      utilization: c.utilization_pct,
                      status: c.status,
                    }))}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="#2D3139" />
                    <XAxis
                      dataKey="name"
                      tick={{ fill: "#8B949E", fontSize: 12 }}
                      angle={-20}
                      textAnchor="end"
                      height={60}
                    />
                    <YAxis
                      tick={{ fill: "#8B949E", fontSize: 12 }}
                      tickFormatter={(v: number) => `${v}%`}
                      domain={[0, 100]}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "#161B22",
                        border: "1px solid #30363D",
                        borderRadius: 8,
                      }}
                      formatter={(v) => [
                        `${Number(v).toFixed(1)}%`,
                        "Utilization",
                      ]}
                    />
                    <ReferenceLine
                      y={90}
                      stroke="#F85149"
                      strokeDasharray="4 4"
                      label={{ value: "Critical 90%", fill: "#F85149", fontSize: 11 }}
                    />
                    <ReferenceLine
                      y={75}
                      stroke="#D29922"
                      strokeDasharray="4 4"
                      label={{ value: "High 75%", fill: "#D29922", fontSize: 11 }}
                    />
                    <Bar dataKey="utilization" radius={[4, 4, 0, 0]}>
                      {capacity.map((c, index) => (
                        <Cell
                          key={index}
                          fill={
                            c.status === "CRITICAL"
                              ? "#F85149"
                              : c.status === "HIGH"
                                ? "#D29922"
                                : c.status === "MODERATE"
                                  ? "#58A6FF"
                                  : "#2EA043"
                          }
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
