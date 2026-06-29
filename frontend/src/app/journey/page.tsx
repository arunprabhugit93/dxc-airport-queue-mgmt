"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useClock } from "@/components/clock-context";
import { api, AIRPORT_CODES, AREA_LABELS, SLA_COLORS } from "@/lib/api";
import type { JourneyStage } from "@/lib/api";
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
import {
  AlertTriangle,
  ArrowRight,
  Clock,
  MapPin,
  Users,
  CheckCircle2,
  ArrowUpRight,
} from "lucide-react";

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

function journeyHealthScore(stages: JourneyStage[]): number {
  if (!stages.length) return 0;
  const points = stages.reduce((sum, s) => {
    if (s.status === "OK") return sum + 1;
    if (s.status === "WARNING") return sum + 0.5;
    return sum; // BREACH = 0 points
  }, 0);
  return Math.round((points / stages.length) * 100);
}

function healthLabel(score: number): { text: string; color: string } {
  if (score >= 90) return { text: "Excellent", color: "#2EA043" };
  if (score >= 70) return { text: "Good", color: "#58A6FF" };
  if (score >= 50) return { text: "Degraded", color: "#D29922" };
  return { text: "Poor", color: "#F85149" };
}

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

  const healthScore = journeyHealthScore(stages);
  const health = healthLabel(healthScore);
  const bottleneckStage = stages.find((s) => s.stage === bottleneck);
  const bottleneckPct =
    totalJourney > 0 && bottleneckStage
      ? ((bottleneckStage.avg_wait_min / totalJourney) * 100).toFixed(0)
      : "0";

  const barData = stages.map((s) => ({
    name: STAGE_LABELS[s.stage] || s.stage,
    wait: s.avg_wait_min,
    pct: totalJourney > 0 ? ((s.avg_wait_min / totalJourney) * 100).toFixed(0) : "0",
  }));

  const pieData = stages
    .filter((s) => s.avg_wait_min > 0)
    .map((s) => ({
      name: STAGE_LABELS[s.stage] || s.stage,
      value: s.avg_wait_min,
    }));

  const bottleneckLinksToStaffing = bottleneck === "SECURITY_TSA" || bottleneck === "SECURITY_PRECHECK";

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
        <div className="text-muted-foreground py-20 text-center">Loading…</div>
      ) : (
        <>
          {/* Narrative Banner */}
          <Card
            className={
              healthScore >= 70
                ? "border-green-500/30 bg-green-500/5"
                : healthScore >= 50
                  ? "border-yellow-500/30 bg-yellow-500/5"
                  : "border-red-500/30 bg-red-500/5"
            }
          >
            <CardContent className="flex items-start gap-3 py-5">
              {healthScore >= 70 ? (
                <CheckCircle2 className="h-5 w-5 text-green-500 shrink-0 mt-0.5" />
              ) : (
                <AlertTriangle
                  className={`h-5 w-5 shrink-0 mt-0.5 ${healthScore < 50 ? "text-red-500" : "text-yellow-500"}`}
                />
              )}
              <div>
                <p className="text-sm font-medium leading-relaxed">
                  A passenger arriving now at <strong>{airport}</strong> will
                  spend approximately{" "}
                  <strong>{totalJourney.toFixed(0)} min</strong> in the airport
                  before boarding.
                  {bottleneckStage && (
                    <>
                      {" "}
                      The main delay is at{" "}
                      <strong>
                        {STAGE_LABELS[bottleneck] || bottleneck}
                      </strong>{" "}
                      at {bottleneckStage.avg_wait_min.toFixed(1)} min (
                      {bottleneckPct}% of the journey).
                    </>
                  )}
                </p>
                {bottleneckLinksToStaffing && bottleneckStage?.status !== "OK" && (
                  <Link
                    href="/staffing"
                    className="inline-flex items-center gap-1 mt-2 text-xs text-blue-400 hover:text-blue-300 transition-colors"
                  >
                    View staffing options to reduce this bottleneck
                    <ArrowUpRight className="h-3 w-3" />
                  </Link>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Hero Metrics */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Total Journey */}
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-7">
                <Clock className="h-7 w-7 text-blue-500 mb-2" />
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

            {/* Journey Health */}
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-7">
                <div
                  className="text-5xl font-bold"
                  style={{ color: health.color }}
                >
                  {healthScore}
                  <span className="text-lg font-normal ml-1">/100</span>
                </div>
                <div
                  className="text-sm font-semibold mt-1"
                  style={{ color: health.color }}
                >
                  {health.text}
                </div>
                <div className="text-xs text-muted-foreground mt-1">
                  Journey Health Score
                </div>
              </CardContent>
            </Card>

            {/* Bottleneck */}
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-7">
                <MapPin className="h-7 w-7 text-red-500 mb-2" />
                <div className="text-2xl font-bold text-center">
                  {STAGE_LABELS[bottleneck] || bottleneck}
                </div>
                {bottleneckStage && (
                  <div className="mt-2">
                    <StatusBadge status={bottleneckStage.status} />
                  </div>
                )}
                <div className="text-xs text-muted-foreground mt-2">
                  Primary Bottleneck
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Journey Flow — proportional width bars */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Journey Flow</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-stretch gap-2 overflow-x-auto pb-2">
                {stages.map((s, i) => {
                  const pct =
                    totalJourney > 0
                      ? ((s.avg_wait_min / totalJourney) * 100).toFixed(0)
                      : "0";
                  const isBottleneck = s.stage === bottleneck && s.status !== "OK";
                  return (
                    <div key={s.stage} className="flex items-center gap-2">
                      <div
                        className={`flex flex-col items-center border rounded-lg p-4 min-w-[150px] ${
                          isBottleneck
                            ? "border-red-500/50 bg-red-500/5"
                            : "border-border bg-card"
                        }`}
                      >
                        <div className="text-xs text-muted-foreground uppercase tracking-wider mb-1">
                          {STAGE_LABELS[s.stage] || s.stage}
                        </div>
                        <div className="text-2xl font-bold mb-0.5">
                          {s.avg_wait_min.toFixed(1)}
                          <span className="text-xs font-normal text-muted-foreground ml-0.5">
                            min
                          </span>
                        </div>
                        <div className="text-xs text-muted-foreground mb-2">
                          {pct}% of journey
                        </div>
                        <StatusBadge status={s.status} />
                        {isBottleneck && (
                          <div className="text-[10px] text-red-500 font-semibold mt-1.5 uppercase tracking-wider">
                            Bottleneck
                          </div>
                        )}
                      </div>
                      {i < stages.length - 1 && (
                        <ArrowRight className="h-5 w-5 text-muted-foreground shrink-0" />
                      )}
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>

          {/* Stage Detail Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {stages.map((s) => (
              <Card key={s.stage}>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-base">
                      {STAGE_LABELS[s.stage] || s.stage}
                    </CardTitle>
                    <StatusBadge status={s.status} />
                  </div>
                </CardHeader>
                <CardContent>
                  <p className="text-xs text-muted-foreground mb-3">
                    {STAGE_DESCRIPTIONS[s.stage] || "Processing stage"}
                  </p>
                  <div className="grid grid-cols-3 gap-2 text-sm">
                    <div>
                      <div className="text-xs text-muted-foreground">Wait</div>
                      <div
                        className="font-semibold"
                        style={{
                          color:
                            s.status === "BREACH"
                              ? SLA_COLORS.BREACH
                              : s.status === "WARNING"
                                ? SLA_COLORS.WARNING
                                : undefined,
                        }}
                      >
                        {s.avg_wait_min.toFixed(1)} m
                      </div>
                    </div>
                    <div>
                      <div className="text-xs text-muted-foreground">Queue</div>
                      <div className="font-semibold">{s.queue_length} pax</div>
                    </div>
                    <div>
                      <div className="text-xs text-muted-foreground">Share</div>
                      <div className="font-semibold">
                        {totalJourney > 0
                          ? `${((s.avg_wait_min / totalJourney) * 100).toFixed(0)}%`
                          : "—"}
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>

          {/* Charts */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Wait Time by Stage</CardTitle>
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
                        formatter={(v, _name, props) => [
                          `${Number(v).toFixed(1)} min (${props.payload?.pct}% of journey)`,
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

            <Card>
              <CardHeader>
                <CardTitle className="text-base">
                  Time Proportion by Stage
                </CardTitle>
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

          {/* Action CTA */}
          {bottleneckStage && bottleneckStage.status !== "OK" && (
            <Card className="border-blue-500/20 bg-blue-500/5">
              <CardContent className="flex items-center justify-between py-4 gap-4">
                <div className="flex items-center gap-3">
                  <Users className="h-5 w-5 text-blue-500 shrink-0" />
                  <div>
                    <p className="text-sm font-semibold">
                      Reduce the {STAGE_LABELS[bottleneck] || bottleneck}{" "}
                      bottleneck
                    </p>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      Get staffing recommendations and run what-if scenarios to
                      bring wait time within SLA.
                    </p>
                  </div>
                </div>
                <div className="flex gap-2 shrink-0">
                  <Link
                    href="/staffing"
                    className="text-xs bg-blue-600 hover:bg-blue-700 text-white px-3 py-1.5 rounded-md transition-colors"
                  >
                    Staffing Plan
                  </Link>
                  <Link
                    href="/simulator"
                    className="text-xs border border-border text-muted-foreground hover:text-foreground hover:bg-muted px-3 py-1.5 rounded-md transition-colors"
                  >
                    Simulator
                  </Link>
                </div>
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
