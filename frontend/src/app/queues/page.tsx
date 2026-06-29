"use client";

import { useEffect, useState } from "react";
import { useClock } from "@/components/clock-context";
import {
  api,
  AIRPORT_CODES,
  AREA_LABELS,
  SLA_COLORS,
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
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { AlertTriangle, Users, Clock, Layers } from "lucide-react";
import type { HeatmapCell } from "@/lib/api";

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

export default function QueuesPage() {
  const { demoNow } = useClock();
  const [airport, setAirport] = useState(AIRPORT_CODES[0]);
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
          api.getHeatmap(airport),
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
  }, [demoNow, airport]);

  const barData = queues.map((q) => ({
    name: AREA_LABELS[q.area_type] || q.area_type,
    wait: q.wait_min,
    queue: q.queue_length,
  }));

  const capacityBarData = capacity.map((c) => ({
    name: AREA_LABELS[c.area_type] || c.area_type,
    utilization: c.utilization_pct,
    headroom: c.headroom_pax,
  }));

  // Build heatmap grid: 7 days x 24 hours
  const heatGrid: number[][] = Array.from({ length: 7 }, () =>
    Array(24).fill(0)
  );
  heatmap.forEach((cell) => {
    if (cell.day_of_week >= 0 && cell.day_of_week < 7 && cell.hour >= 0 && cell.hour < 24) {
      heatGrid[cell.day_of_week][cell.hour] = cell.avg_wait_min;
    }
  });

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
        <h1 className="text-2xl font-bold">Queue Intelligence</h1>
        <Select value={airport} onValueChange={(v) => v && setAirport(v)}>
          <SelectTrigger className="w-40">
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

      {loading ? (
        <div className="text-muted-foreground py-20 text-center">
          Loading...
        </div>
      ) : (
        <>
          {/* Area Queue Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {queues.map((q) => (
              <Card key={q.area_type}>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <CardTitle>
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
                      <div className="font-semibold text-lg">
                        {q.wait_min.toFixed(1)}
                        <span className="text-xs font-normal text-muted-foreground ml-0.5">
                          min
                        </span>
                      </div>
                    </div>
                    <div>
                      <div className="text-xs text-muted-foreground flex items-center gap-1">
                        <Layers className="h-3 w-3" />
                        Depth
                      </div>
                      <div className="font-semibold text-lg">
                        {q.queue_length}
                      </div>
                    </div>
                    <div>
                      <div className="text-xs text-muted-foreground flex items-center gap-1">
                        <Users className="h-3 w-3" />
                        Staff
                      </div>
                      <div className="font-semibold text-lg">
                        {q.staff_on_duty}
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>

          {/* Area Comparison Bar Chart */}
          <Card>
            <CardHeader>
              <CardTitle>Area Comparison</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={barData}>
                    <CartesianGrid
                      strokeDasharray="3 3"
                      stroke="#2D3139"
                    />
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
                    <Bar
                      dataKey="wait"
                      fill="#0080FF"
                      radius={[4, 4, 0, 0]}
                      name="wait"
                    />
                    <Bar
                      dataKey="queue"
                      fill="#58A6FF"
                      radius={[4, 4, 0, 0]}
                      name="queue"
                      opacity={0.6}
                    />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>

          {/* Heatmap */}
          <Card>
            <CardHeader>
              <CardTitle>
                Wait Time Heatmap{" "}
                <span className="text-sm font-normal text-muted-foreground">
                  (Hour x Day of Week)
                </span>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <div className="min-w-[700px]">
                  {/* Hour labels */}
                  <div className="flex ml-12 mb-1">
                    {Array.from({ length: 24 }, (_, h) => (
                      <div
                        key={h}
                        className="flex-1 text-center text-[10px] text-muted-foreground"
                      >
                        {h}
                      </div>
                    ))}
                  </div>
                  {/* Grid rows */}
                  {heatGrid.map((row, dayIdx) => (
                    <div key={dayIdx} className="flex items-center gap-1 mb-1">
                      <div className="w-10 text-xs text-muted-foreground text-right pr-2">
                        {DAY_NAMES[dayIdx]}
                      </div>
                      <div className="flex flex-1 gap-0.5">
                        {row.map((val, hourIdx) => (
                          <div
                            key={hourIdx}
                            className={`flex-1 h-6 rounded-sm ${heatColor(val)} cursor-default`}
                            title={`${DAY_NAMES[dayIdx]} ${hourIdx}:00 — ${val.toFixed(1)} min`}
                          />
                        ))}
                      </div>
                    </div>
                  ))}
                  {/* Legend */}
                  <div className="flex items-center gap-2 mt-4 ml-12 text-xs text-muted-foreground">
                    <span>Low</span>
                    <div className="flex gap-0.5">
                      <div className="w-6 h-3 rounded-sm bg-green-900" />
                      <div className="w-6 h-3 rounded-sm bg-green-700" />
                      <div className="w-6 h-3 rounded-sm bg-yellow-700" />
                      <div className="w-6 h-3 rounded-sm bg-orange-700" />
                      <div className="w-6 h-3 rounded-sm bg-red-700" />
                      <div className="w-6 h-3 rounded-sm bg-red-900" />
                    </div>
                    <span>High</span>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Capacity Utilization */}
          <Card>
            <CardHeader>
              <CardTitle>Capacity Utilization</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={capacityBarData}>
                    <CartesianGrid
                      strokeDasharray="3 3"
                      stroke="#2D3139"
                    />
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
                      formatter={(v, name) => [
                        name === "utilization"
                          ? `${Number(v).toFixed(1)}%`
                          : `${v} pax`,
                        name === "utilization"
                          ? "Utilization"
                          : "Headroom",
                      ]}
                    />
                    <Bar
                      dataKey="utilization"
                      fill="#D29922"
                      radius={[4, 4, 0, 0]}
                      name="utilization"
                    />
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
