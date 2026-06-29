"use client";

import { useState, useMemo } from "react";
import { useClock } from "@/components/clock-context";
import { api, AIRPORT_CODES, AREA_LABELS, type StaffingHour } from "@/lib/api";
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
import { Users, Download, AlertCircle } from "lucide-react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Line,
  ComposedChart,
  ReferenceLine,
  Cell,
} from "recharts";

const COST_PER_HOUR = 35;
const CH = { grid: "#e2e8f0", tick: "#94a3b8", sky: "#0ea5e9", amber: "#d97706", green: "#16a34a", red: "#dc2626" };

export default function StaffingPage() {
  const { demoNow } = useClock();
  const [airport, setAirport] = useState("ATL");
  const [date, setDate] = useState(() => demoNow ? demoNow.slice(0, 10) : "2021-11-24");
  const [area, setArea] = useState("SECURITY_TSA");
  const [slaTarget, setSlaTarget] = useState(10);
  const [hours, setHours] = useState<StaffingHour[]>([]);
  const [totals, setTotals] = useState<{ peak_lanes: number; total_staff_hours: number } | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);

  async function loadStaffing() {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getStaffing(airport, date, area, slaTarget);
      setHours(data.hours);
      setTotals(data.totals);
      setLoaded(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load staffing data");
    } finally {
      setLoading(false);
    }
  }

  const slaCompliance = useMemo(() => {
    if (hours.length === 0) return 0;
    const met = hours.filter((h) => h.sla_met).length;
    return (met / hours.length) * 100;
  }, [hours]);

  const hoursMeetingSLA = hours.filter((h) => h.sla_met).length;
  const estimatedCost = totals ? totals.total_staff_hours * COST_PER_HOUR : 0;

  const slaGaps = useMemo(() => {
    return hours
      .filter((h) => !h.sla_met)
      .map((h) => ({
        hour: h.rec_hour,
        expected_wait: h.expected_wait_min,
        overshoot: h.expected_wait_min - slaTarget,
      }));
  }, [hours, slaTarget]);

  const chartData = hours.map((h) => ({
    hour: `${String(h.rec_hour).padStart(2, "0")}:00`,
    recommended_lanes: h.recommended_lanes,
    forecast_pax: h.forecast_pax,
    sla_met: h.sla_met,
    expected_wait: h.expected_wait_min,
    staff: h.recommended_staff,
  }));

  function downloadCSV() {
    const header = "Hour,Forecast Pax,Recommended Lanes,Staff,Expected Wait (min),SLA Met\n";
    const rows = hours.map((h) =>
      `${h.rec_hour},${h.forecast_pax},${h.recommended_lanes},${h.recommended_staff},${h.expected_wait_min.toFixed(1)},${h.sla_met}`
    ).join("\n");
    const blob = new Blob([header + rows], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `staffing-${airport}-${date}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center gap-2 mb-2">
        <Users className="h-6 w-6 text-blue-500" />
        <h1 className="text-2xl font-bold text-foreground">Staff & Lane Optimizer</h1>
      </div>

      {/* Controls */}
      <div className="flex flex-wrap items-end gap-4 bg-card border border-border rounded-lg p-4">
        <div className="flex flex-col gap-1">
          <label className="text-xs text-muted-foreground uppercase tracking-wider">Airport</label>
          <Select value={airport} onValueChange={(v) => v && setAirport(v)}>
            <SelectTrigger className="w-[120px]">
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
          <label className="text-xs text-muted-foreground uppercase tracking-wider">Date</label>
          <input
            type="date" min="2020-02-15" max="2022-10-15"
            value={date}
            onChange={(e) => setDate(e.target.value)}
            className="h-8 rounded-lg border border-input bg-transparent px-2.5 text-sm text-foreground outline-none focus:border-ring focus:ring-3 focus:ring-ring/50"
          />
        </div>

        <div className="flex flex-col gap-1">
          <label className="text-xs text-muted-foreground uppercase tracking-wider">Area</label>
          <Select value={area} onValueChange={(v) => v && setArea(v)}>
            <SelectTrigger className="w-[160px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {Object.entries(AREA_LABELS).map(([key, label]) => (
                <SelectItem key={key} value={key}>{label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="flex flex-col gap-1 min-w-[180px]">
          <label className="text-xs text-muted-foreground uppercase tracking-wider">
            SLA Target: {slaTarget} min
          </label>
          <Slider
            min={5}
            max={20}
            value={[slaTarget]}
            onValueChange={(v) => setSlaTarget(Array.isArray(v) ? v[0] : v)}
          />
        </div>

        <Button onClick={loadStaffing} disabled={loading}>
          {loading ? "Loading..." : "Recommend"}
        </Button>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 text-red-400">
          <AlertCircle className="inline h-4 w-4 mr-2" />
          {error}
        </div>
      )}

      {loading && (
        <div className="flex items-center justify-center h-64 text-muted-foreground">
          <div className="animate-pulse">Computing optimal staffing...</div>
        </div>
      )}

      {loaded && !loading && (
        <>
          {/* Summary KPI Cards */}
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            <MetricCard
              label="Peak Lanes"
              value={totals?.peak_lanes ?? 0}
              accentColor="#0080FF"
            />
            <MetricCard
              label="Total Staff-Hours"
              value={totals?.total_staff_hours ?? 0}
              accentColor="#58A6FF"
            />
            <MetricCard
              label="SLA Compliance"
              value={`${slaCompliance.toFixed(0)}%`}
              sublabel={`${hoursMeetingSLA}/${hours.length} hours`}
              accentColor={slaCompliance >= 80 ? "#2EA043" : "#F85149"}
            />
            <MetricCard
              label="Hours Meeting SLA"
              value={hoursMeetingSLA}
              sublabel={`of ${hours.length} total`}
              accentColor="#2EA043"
            />
            <MetricCard
              label="Estimated Cost"
              value={`$${estimatedCost.toLocaleString()}`}
              sublabel={`@ $${COST_PER_HOUR}/hr`}
              accentColor="#D29922"
            />
          </div>

          {/* Schedule Chart */}
          <Card>
            <CardHeader>
              <CardTitle>Hourly Staffing Schedule</CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={350}>
                <ComposedChart data={chartData} margin={{ top: 10, right: 40, bottom: 20, left: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke={CH.grid} />
                  <XAxis dataKey="hour" tick={{ fill: CH.tick, fontSize: 12 }} stroke={CH.grid} />
                  <YAxis
                    yAxisId="left"
                    tick={{ fill: CH.tick, fontSize: 12 }}
                    stroke={CH.grid}
                    label={{ value: "Lanes", angle: -90, position: "insideLeft", fill: CH.tick }}
                  />
                  <YAxis
                    yAxisId="right"
                    orientation="right"
                    tick={{ fill: CH.tick, fontSize: 12 }}
                    stroke={CH.grid}
                    label={{ value: "Passengers", angle: 90, position: "insideRight", fill: CH.tick }}
                  />
                  <Tooltip
                    contentStyle={{ backgroundColor: "var(--card)", border: "1px solid var(--border)", borderRadius: 8 }}
                    labelStyle={{ color: "var(--foreground)" }}
                  />
                  {/* Shift boundaries */}
                  <ReferenceLine x="06:00" yAxisId="left" stroke={CH.sky} strokeDasharray="5 5" label={{ value: "Shift 1", fill: CH.sky, fontSize: 11 }} />
                  <ReferenceLine x="14:00" yAxisId="left" stroke={CH.sky} strokeDasharray="5 5" label={{ value: "Shift 2", fill: CH.sky, fontSize: 11 }} />
                  <ReferenceLine x="22:00" yAxisId="left" stroke={CH.sky} strokeDasharray="5 5" label={{ value: "Shift 3", fill: CH.sky, fontSize: 11 }} />

                  <Bar yAxisId="left" dataKey="recommended_lanes" radius={[4, 4, 0, 0]} name="Recommended Lanes">
                    {chartData.map((entry, i) => (
                      <Cell key={i} fill={entry.sla_met ? "#2EA043" : "#F85149"} />
                    ))}
                  </Bar>
                  <Line
                    yAxisId="right"
                    type="monotone"
                    dataKey="forecast_pax"
                    stroke={CH.amber}
                    strokeWidth={2}
                    dot={false}
                    name="Forecast Pax"
                  />
                </ComposedChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          {/* SLA Gap Analysis */}
          {slaGaps.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-red-400">SLA Gap Analysis</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {slaGaps.map((gap) => (
                    <div key={gap.hour} className="flex items-center gap-3 bg-red-500/10 border border-red-500/20 rounded-lg px-4 py-2">
                      <AlertCircle className="h-4 w-4 text-red-400 shrink-0" />
                      <span className="text-sm font-mono">{String(gap.hour).padStart(2, "0")}:00</span>
                      <span className="text-sm text-muted-foreground">
                        Expected wait: {gap.expected_wait.toFixed(1)} min
                      </span>
                      <span className="text-sm text-red-400 font-medium ml-auto">
                        +{gap.overshoot.toFixed(1)} min over SLA
                      </span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Hourly Schedule Table */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>Hourly Schedule</CardTitle>
              <Button variant="outline" size="sm" onClick={downloadCSV}>
                <Download className="h-4 w-4 mr-1" />
                Download CSV
              </Button>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border text-left">
                      <th className="py-2 px-3 text-muted-foreground font-medium">Hour</th>
                      <th className="py-2 px-3 text-muted-foreground font-medium">Forecast Pax</th>
                      <th className="py-2 px-3 text-muted-foreground font-medium">Lanes</th>
                      <th className="py-2 px-3 text-muted-foreground font-medium">Staff</th>
                      <th className="py-2 px-3 text-muted-foreground font-medium">Expected Wait</th>
                      <th className="py-2 px-3 text-muted-foreground font-medium">SLA</th>
                    </tr>
                  </thead>
                  <tbody>
                    {hours.map((h) => (
                      <tr key={h.rec_hour} className="border-b border-border/50 hover:bg-muted/30">
                        <td className="py-2 px-3 font-mono">{String(h.rec_hour).padStart(2, "0")}:00</td>
                        <td className="py-2 px-3">{h.forecast_pax}</td>
                        <td className="py-2 px-3 font-semibold">{h.recommended_lanes}</td>
                        <td className="py-2 px-3">{h.recommended_staff}</td>
                        <td className="py-2 px-3 font-mono">{h.expected_wait_min.toFixed(1)} min</td>
                        <td className="py-2 px-3">
                          <span className={`px-2 py-0.5 rounded text-xs font-semibold ${h.sla_met ? "bg-green-500/20 text-green-400" : "bg-red-500/20 text-red-400"}`}>
                            {h.sla_met ? "MET" : "BREACH"}
                          </span>
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
