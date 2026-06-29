"use client";

import { useEffect, useState } from "react";
import { useClock } from "@/components/clock-context";
import {
  api,
  AIRPORT_CODES,
  AREA_LABELS,
  SLA_COLORS,
} from "@/lib/api";
import type { JourneyStage } from "@/lib/api";
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
  PieChart,
  Pie,
  Cell,
  Legend,
} from "recharts";
import { AlertTriangle, ArrowRight, Clock, MapPin } from "lucide-react";

const STAGE_DESCRIPTIONS: Record<string, string> = {
  CHECKIN: "Document verification, boarding pass, bag drop",
  SECURITY_TSA: "ID check, X-ray screening, metal detector",
  IMMIGRATION: "Passport control, customs, border clearance",
  GATE: "Boarding zone, final check, jet bridge",
  BAGGAGE: "Carousel wait, bag retrieval",
};

const STAGE_LABELS: Record<string, string> = {
  CHECKIN: "Check-in",
  SECURITY_TSA: "TSA Security",
  IMMIGRATION: "Immigration",
  GATE: "Gate",
  BAGGAGE: "Baggage",
};

const PIE_COLORS = ["#0080FF", "#58A6FF", "#D29922", "#2EA043", "#F85149"];

export default function JourneyPage() {
  const { demoNow } = useClock();
  const [airport, setAirport] = useState(AIRPORT_CODES[0]);
  const [stages, setStages] = useState<JourneyStage[]>([]);
  const [totalJourney, setTotalJourney] = useState(0);
  const [bottleneck, setBottleneck] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const res = await api.getJourney(airport);
        if (cancelled) return;
        setStages(res.stages);
        setTotalJourney(res.total_journey_min);
        setBottleneck(res.bottleneck);
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

  const barData = stages.map((s) => ({
    name: STAGE_LABELS[s.stage] || s.stage,
    wait: s.avg_wait_min,
  }));

  const pieData = stages.map((s) => ({
    name: STAGE_LABELS[s.stage] || s.stage,
    value: s.avg_wait_min,
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
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Passenger Journey</h1>
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
          {/* Hero Metrics */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-8">
                <Clock className="h-8 w-8 text-blue-500 mb-3" />
                <div className="text-5xl font-bold">
                  {totalJourney.toFixed(0)}
                  <span className="text-lg text-muted-foreground font-normal ml-1">
                    min
                  </span>
                </div>
                <div className="text-sm text-muted-foreground mt-2">
                  Total Journey Time
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-8">
                <MapPin className="h-8 w-8 text-red-500 mb-3" />
                <div className="text-3xl font-bold">
                  {STAGE_LABELS[bottleneck] || bottleneck}
                </div>
                <div className="text-sm text-muted-foreground mt-2">
                  Bottleneck Identified
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Journey Flow */}
          <Card>
            <CardHeader>
              <CardTitle>Journey Flow</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-stretch gap-2 overflow-x-auto pb-2">
                {stages.map((s, i) => (
                  <div key={s.stage} className="flex items-center gap-2">
                    <div className="flex flex-col items-center border border-border rounded-lg p-4 min-w-[160px] bg-card">
                      <div className="text-xs text-muted-foreground uppercase tracking-wider mb-1">
                        {STAGE_LABELS[s.stage] || s.stage}
                      </div>
                      <div className="text-2xl font-bold mb-1">
                        {s.avg_wait_min.toFixed(1)}
                        <span className="text-xs font-normal text-muted-foreground ml-0.5">
                          min
                        </span>
                      </div>
                      <div className="text-xs text-muted-foreground mb-2">
                        Queue: {s.queue_length} pax
                      </div>
                      <StatusBadge status={s.status} />
                    </div>
                    {i < stages.length - 1 && (
                      <ArrowRight className="h-5 w-5 text-muted-foreground shrink-0" />
                    )}
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Stage Details */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {stages.map((s) => (
              <Card key={s.stage}>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <CardTitle>{STAGE_LABELS[s.stage] || s.stage}</CardTitle>
                    <StatusBadge status={s.status} />
                  </div>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground mb-3">
                    {STAGE_DESCRIPTIONS[s.stage] || "Processing stage"}
                  </p>
                  <div className="grid grid-cols-2 gap-3 text-sm">
                    <div>
                      <div className="text-xs text-muted-foreground">
                        Avg Wait
                      </div>
                      <div className="font-semibold">
                        {s.avg_wait_min.toFixed(1)} min
                      </div>
                    </div>
                    <div>
                      <div className="text-xs text-muted-foreground">
                        Queue Depth
                      </div>
                      <div className="font-semibold">{s.queue_length} pax</div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>

          {/* Charts row */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Wait Time Breakdown Bar Chart */}
            <Card>
              <CardHeader>
                <CardTitle>Wait Time Breakdown</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="h-72">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      data={barData}
                      layout="vertical"
                      margin={{ left: 20 }}
                    >
                      <CartesianGrid
                        strokeDasharray="3 3"
                        stroke="#2D3139"
                        horizontal={false}
                      />
                      <XAxis
                        type="number"
                        tick={{ fill: "#8B949E", fontSize: 12 }}
                        tickFormatter={(v: number) => `${v}m`}
                      />
                      <YAxis
                        type="category"
                        dataKey="name"
                        tick={{ fill: "#8B949E", fontSize: 12 }}
                        width={100}
                      />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: "#161B22",
                          border: "1px solid #30363D",
                          borderRadius: 8,
                        }}
                        formatter={(v) => [
                          `${Number(v).toFixed(1)} min`,
                          "Wait",
                        ]}
                      />
                      <Bar
                        dataKey="wait"
                        fill="#0080FF"
                        radius={[0, 4, 4, 0]}
                      />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>

            {/* Time Proportion Donut */}
            <Card>
              <CardHeader>
                <CardTitle>Time Proportion by Stage</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="h-72">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={pieData}
                        cx="50%"
                        cy="50%"
                        innerRadius={60}
                        outerRadius={100}
                        paddingAngle={3}
                        dataKey="value"
                        nameKey="name"
                        label={(entry) =>
                          `${entry.name} ${((entry.percent ?? 0) * 100).toFixed(0)}%`
                        }
                      >
                        {pieData.map((_, i) => (
                          <Cell
                            key={i}
                            fill={PIE_COLORS[i % PIE_COLORS.length]}
                          />
                        ))}
                      </Pie>
                      <Tooltip
                        contentStyle={{
                          backgroundColor: "#161B22",
                          border: "1px solid #30363D",
                          borderRadius: 8,
                        }}
                        formatter={(v) => [
                          `${Number(v).toFixed(1)} min`,
                          "Wait Time",
                        ]}
                      />
                      <Legend />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>
          </div>
        </>
      )}
    </div>
  );
}
