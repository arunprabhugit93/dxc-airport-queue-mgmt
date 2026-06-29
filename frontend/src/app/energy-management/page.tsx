"use client";

import { useEffect, useMemo, useState } from "react";
import { useClock } from "@/components/clock-context";
import { MetricCard } from "@/components/metric-card";
import { StatusBadge } from "@/components/status-badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { api, AIRPORT_CODES } from "@/lib/api";
import type {
  EnergyAirportSummary,
  EnergyRecommendation,
  EnergySetpointSimulation,
  EnergyTemperaturePoint,
  EnergyTerminalStatus,
} from "@/lib/api";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  Activity,
  AlertTriangle,
  BatteryCharging,
  Building2,
  CloudSun,
  DollarSign,
  Factory,
  Gauge,
  Leaf,
  Thermometer,
  Zap,
} from "lucide-react";

function money(value: number): string {
  return `$${Math.round(value).toLocaleString()}`;
}

function compact(value: number): string {
  return Math.round(value).toLocaleString();
}

export default function EnergyManagementPage() {
  const { demoNow } = useClock();
  const [airport, setAirport] = useState(AIRPORT_CODES[0]);
  const [overview, setOverview] = useState<EnergyAirportSummary[]>([]);
  const [terminals, setTerminals] = useState<EnergyTerminalStatus[]>([]);
  const [profile, setProfile] = useState<EnergyTemperaturePoint[]>([]);
  const [recommendations, setRecommendations] = useState<EnergyRecommendation[]>([]);
  const [simulation, setSimulation] = useState<EnergySetpointSimulation | null>(null);
  const [setpointDelta, setSetpointDelta] = useState(2);
  const [durationHours, setDurationHours] = useState(8);
  const [tariff, setTariff] = useState(0);
  const [loading, setLoading] = useState(true);
  const [simLoading, setSimLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const [overviewRes, terminalsRes, profileRes, recRes] = await Promise.all([
          api.getEnergyOverview(),
          api.getEnergyTerminals(airport),
          api.getEnergyTemperatureProfile(airport),
          api.getEnergyRecommendations(airport),
        ]);
        if (cancelled) return;
        setOverview(overviewRes.airports);
        setTariff(overviewRes.tariff_usd_per_kwh);
        setTerminals(terminalsRes.terminals);
        setProfile(profileRes.points);
        setRecommendations(recRes.recommendations);
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : "Failed to load energy data");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [airport, demoNow]);

  useEffect(() => {
    let cancelled = false;
    async function simulate() {
      setSimLoading(true);
      try {
        const result = await api.simulateEnergySetpoint({
          airport_code: airport,
          setpoint_delta_f: setpointDelta,
          duration_hours: durationHours,
        });
        if (!cancelled) setSimulation(result);
      } catch {
        if (!cancelled) setSimulation(null);
      } finally {
        if (!cancelled) setSimLoading(false);
      }
    }
    simulate();
    return () => {
      cancelled = true;
    };
  }, [airport, setpointDelta, durationHours, demoNow]);

  const selectedAirport = overview.find((item) => item.airport_code === airport);
  const network = useMemo(
    () => ({
      load: overview.reduce((sum, item) => sum + item.current_load_kw, 0),
      cost: overview.reduce((sum, item) => sum + item.daily_cost_usd, 0),
      carbon: overview.reduce((sum, item) => sum + item.carbon_kg, 0),
    }),
    [overview]
  );
  const terminalLoadData = terminals.map((terminal) => ({
    name: terminal.terminal,
    hvac: terminal.hvac_load_kw,
    lighting: terminal.lighting_load_kw,
    plug: terminal.plug_load_kw,
    charging: terminal.charging_load_kw,
  }));
  const peakPoint = profile.reduce<EnergyTemperaturePoint | null>(
    (peak, point) => (!peak || point.total_load_kw > peak.total_load_kw ? point : peak),
    null
  );
  const forecastData = profile.map((point) => ({
    hour: point.hour,
    load: point.total_load_kw,
    hvac: point.hvac_load_kw,
    outdoor: point.outdoor_temp_f,
    peakLimit: selectedAirport ? selectedAirport.current_load_kw * 1.08 : 0,
  }));
  const demandResponse = terminals.map((terminal) => {
    const shedKw = terminal.hvac_load_kw * 0.08 + terminal.charging_load_kw * 0.35;
    const score = terminal.occupancy_index < 0.45 ? "LOW IMPACT" : terminal.occupancy_index < 0.7 ? "MANAGED" : "CONSTRAINED";
    return {
      terminal: terminal.terminal,
      shedKw,
      score,
      action: terminal.occupancy_index < 0.45
        ? "Dim lighting, defer charging, raise setpoint 2°F"
        : "Defer charging and trim HVAC fan speed",
    };
  });
  const carbonData = profile.map((point) => {
    const solarShape = Math.max(0, Math.sin(((point.hour - 6) / 12) * Math.PI));
    const renewableKw = point.total_load_kw * solarShape * 0.16;
    return {
      hour: point.hour,
      carbonKg: point.total_load_kw * 0.38,
      renewableKw,
      gridKw: Math.max(point.total_load_kw - renewableKw, 0),
    };
  });
  const tariffData = profile.map((point) => {
    const peakTariff = point.hour >= 14 && point.hour <= 19;
    return {
      hour: point.hour,
      cost: point.total_load_kw * (peakTariff ? 0.24 : 0.14),
      load: point.total_load_kw,
      tariff: peakTariff ? "Peak" : "Standard",
    };
  });
  const assetHealth = terminals.map((terminal) => {
    const hvacShare = terminal.hvac_load_kw / Math.max(terminal.current_load_kw, 1);
    const faultRisk = hvacShare > 0.58 || terminal.comfort_status === "RISK"
      ? "HIGH"
      : hvacShare > 0.50 || terminal.comfort_status === "WATCH"
        ? "MEDIUM"
        : "LOW";
    const probableCause = faultRisk === "HIGH"
      ? "Cooling loop or air-handler running outside expected load band"
      : faultRisk === "MEDIUM"
        ? "Mixed-air economizer or zone schedule needs review"
        : "No abnormal HVAC signature";
    return { ...terminal, hvacShare, faultRisk, probableCause };
  });
  const chargingPlan = terminals.map((terminal) => ({
    terminal: terminal.terminal,
    chargingKw: terminal.charging_load_kw,
    shiftableKw: terminal.charging_load_kw * 0.45,
    priority: terminal.occupancy_index > 0.72 ? "Hold critical chargers only" : "Shift noncritical charging",
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
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Energy Management</h1>
          <div className="text-sm text-muted-foreground mt-1">
            Terminal energy, HVAC load, temperature impact, and savings simulation
          </div>
        </div>
        <Select value={airport} onValueChange={(value) => value && setAirport(value)}>
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
        <div className="text-muted-foreground py-20 text-center">Loading...</div>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
            <MetricCard
              label="Network Load"
              value={`${compact(network.load)} kW`}
              sublabel={`Tariff ${tariff.toFixed(2)} USD/kWh`}
              accentColor="#58A6FF"
            />
            <MetricCard
              label="Daily Cost"
              value={money(network.cost)}
              sublabel="Estimated current operating day"
              accentColor="#D29922"
            />
            <MetricCard
              label="Carbon"
              value={`${compact(network.carbon)} kg`}
              sublabel="Grid emissions estimate"
              accentColor="#2EA043"
            />
            <MetricCard
              label={`${airport} Outdoor`}
              value={`${selectedAirport?.outdoor_temp_f.toFixed(1) ?? "0.0"}°F`}
              sublabel={`Setpoint ${selectedAirport?.indoor_setpoint_f.toFixed(0) ?? "72"}°F`}
              accentColor="#F85149"
            />
          </div>

          <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
            <Card className="xl:col-span-2">
              <CardHeader>
                <div className="flex items-center gap-2">
                  <Zap className="h-4 w-4 text-blue-500" />
                  <CardTitle>Airport Energy Load</CardTitle>
                </div>
              </CardHeader>
              <CardContent>
                <div className="h-80">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={overview}>
                      <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                      <XAxis dataKey="airport_code" />
                      <YAxis />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: "hsl(var(--card))",
                          border: "1px solid hsl(var(--border))",
                          borderRadius: 8,
                        }}
                      />
                      <Bar dataKey="hvac_load_kw" name="HVAC kW" stackId="load" fill="#58A6FF" />
                      <Bar dataKey="current_load_kw" name="Total kW" fill="#2EA043" opacity={0.35} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>

            <Card id="setpoint-lab">
              <CardHeader>
                <div className="flex items-center gap-2">
                  <DollarSign className="h-4 w-4 text-yellow-500" />
                  <CardTitle>Setpoint Simulator</CardTitle>
                </div>
              </CardHeader>
              <CardContent className="space-y-5">
                <div>
                  <div className="flex items-center justify-between text-sm mb-2">
                    <span className="text-muted-foreground">Setpoint delta</span>
                    <span className="font-mono">{setpointDelta > 0 ? "+" : ""}{setpointDelta}°F</span>
                  </div>
                  <input
                    type="range"
                    min={-2}
                    max={6}
                    step={1}
                    value={setpointDelta}
                    onChange={(event) => setSetpointDelta(Number(event.target.value))}
                    className="w-full"
                  />
                </div>
                <div>
                  <div className="flex items-center justify-between text-sm mb-2">
                    <span className="text-muted-foreground">Duration</span>
                    <span className="font-mono">{durationHours}h</span>
                  </div>
                  <input
                    type="range"
                    min={1}
                    max={24}
                    step={1}
                    value={durationHours}
                    onChange={(event) => setDurationHours(Number(event.target.value))}
                    className="w-full"
                  />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div className="border border-border rounded-md p-3">
                    <div className="text-xs text-muted-foreground uppercase">Energy Saved</div>
                    <div className="text-xl font-bold mt-1">
                      {simLoading ? "..." : compact(simulation?.saved_energy_kwh ?? 0)}
                      <span className="text-xs text-muted-foreground ml-1">kWh</span>
                    </div>
                  </div>
                  <div className="border border-border rounded-md p-3">
                    <div className="text-xs text-muted-foreground uppercase">Cost Saved</div>
                    <div className="text-xl font-bold mt-1">
                      {simLoading ? "..." : money(simulation?.saved_cost_usd ?? 0)}
                    </div>
                  </div>
                </div>
                {simulation && (
                  <div className="border border-border rounded-md p-3 text-sm">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-muted-foreground">Comfort risk</span>
                      <StatusBadge status={simulation.comfort_risk} />
                    </div>
                    <p className="text-muted-foreground">{simulation.recommendation}</p>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
            <Card id="load-forecast">
              <CardHeader>
                <div className="flex items-center gap-2">
                  <Thermometer className="h-4 w-4 text-red-500" />
                  <CardTitle>Load Forecast & Weather Driver</CardTitle>
                </div>
              </CardHeader>
              <CardContent>
                <div className="h-80">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={forecastData}>
                      <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                      <XAxis dataKey="hour" />
                      <YAxis yAxisId="left" />
                      <YAxis yAxisId="right" orientation="right" />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: "hsl(var(--card))",
                          border: "1px solid hsl(var(--border))",
                          borderRadius: 8,
                        }}
                      />
                      <Line yAxisId="left" type="monotone" dataKey="load" name="Total kW" stroke="#58A6FF" strokeWidth={2} dot={false} />
                      <Line yAxisId="left" type="monotone" dataKey="hvac" name="HVAC kW" stroke="#2EA043" strokeWidth={2} dot={false} />
                      <Line yAxisId="left" type="monotone" dataKey="peakLimit" name="Peak guardrail" stroke="#D29922" strokeDasharray="4 4" strokeWidth={2} dot={false} />
                      <Line yAxisId="right" type="monotone" dataKey="outdoor" name="Outdoor °F" stroke="#F85149" strokeWidth={2} dot={false} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
                <div className="grid grid-cols-3 gap-3 mt-4 text-sm">
                  <div className="border border-border rounded-md p-3">
                    <div className="text-xs text-muted-foreground uppercase">Peak Hour</div>
                    <div className="font-bold mt-1">{peakPoint ? `${peakPoint.hour}:00` : "—"}</div>
                  </div>
                  <div className="border border-border rounded-md p-3">
                    <div className="text-xs text-muted-foreground uppercase">Peak Load</div>
                    <div className="font-bold mt-1">{compact(peakPoint?.total_load_kw ?? 0)} kW</div>
                  </div>
                  <div className="border border-border rounded-md p-3">
                    <div className="text-xs text-muted-foreground uppercase">Peak HVAC</div>
                    <div className="font-bold mt-1">{compact(peakPoint?.hvac_load_kw ?? 0)} kW</div>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <div className="flex items-center gap-2">
                  <Building2 className="h-4 w-4 text-blue-500" />
                  <CardTitle>Terminal Load Mix</CardTitle>
                </div>
              </CardHeader>
              <CardContent>
                <div className="h-80">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={terminalLoadData}>
                      <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                      <XAxis dataKey="name" />
                      <YAxis />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: "hsl(var(--card))",
                          border: "1px solid hsl(var(--border))",
                          borderRadius: 8,
                        }}
                      />
                      <Area type="monotone" dataKey="hvac" name="HVAC" stackId="1" stroke="#58A6FF" fill="#58A6FF" />
                      <Area type="monotone" dataKey="lighting" name="Lighting" stackId="1" stroke="#D29922" fill="#D29922" />
                      <Area type="monotone" dataKey="plug" name="Plug" stackId="1" stroke="#8B949E" fill="#8B949E" />
                      <Area type="monotone" dataKey="charging" name="Charging" stackId="1" stroke="#2EA043" fill="#2EA043" />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>
          </div>

          <div className="grid grid-cols-1 xl:grid-cols-3 gap-6" id="demand-response">
            <Card className="xl:col-span-2">
              <CardHeader>
                <div className="flex items-center gap-2">
                  <Gauge className="h-4 w-4 text-blue-500" />
                  <CardTitle>Demand Response Dispatch</CardTitle>
                </div>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {demandResponse.map((item) => (
                    <div key={item.terminal} className="border border-border rounded-md p-4">
                      <div className="flex items-center justify-between mb-2">
                        <div className="font-semibold">{item.terminal}</div>
                        <StatusBadge status={item.score === "LOW IMPACT" ? "LOW" : item.score === "MANAGED" ? "MEDIUM" : "HIGH"} />
                      </div>
                      <div className="text-2xl font-bold">
                        {compact(item.shedKw)}
                        <span className="text-xs text-muted-foreground ml-1">kW shed</span>
                      </div>
                      <div className="text-sm text-muted-foreground mt-2">{item.action}</div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            <Card id="tariff-control">
              <CardHeader>
                <div className="flex items-center gap-2">
                  <DollarSign className="h-4 w-4 text-yellow-500" />
                  <CardTitle>Tariff Control</CardTitle>
                </div>
              </CardHeader>
              <CardContent>
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={tariffData}>
                      <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                      <XAxis dataKey="hour" />
                      <YAxis />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: "hsl(var(--card))",
                          border: "1px solid hsl(var(--border))",
                          borderRadius: 8,
                        }}
                      />
                      <Bar dataKey="cost" name="Hourly cost" fill="#D29922" />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
                <div className="text-sm text-muted-foreground mt-3">
                  Peak tariff window: 14:00-19:00. Shift flexible loads before this window where passenger impact is low.
                </div>
              </CardContent>
            </Card>
          </div>

          <div className="grid grid-cols-1 xl:grid-cols-2 gap-6" id="carbon-renewables">
            <Card>
              <CardHeader>
                <div className="flex items-center gap-2">
                  <Leaf className="h-4 w-4 text-green-500" />
                  <CardTitle>Carbon & Renewable Offset</CardTitle>
                </div>
              </CardHeader>
              <CardContent>
                <div className="h-72">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={carbonData}>
                      <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                      <XAxis dataKey="hour" />
                      <YAxis />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: "hsl(var(--card))",
                          border: "1px solid hsl(var(--border))",
                          borderRadius: 8,
                        }}
                      />
                      <Area type="monotone" dataKey="gridKw" name="Grid kW" stackId="1" stroke="#8B949E" fill="#8B949E" />
                      <Area type="monotone" dataKey="renewableKw" name="PV/Battery offset kW" stackId="1" stroke="#2EA043" fill="#2EA043" />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>

            <Card id="charging">
              <CardHeader>
                <div className="flex items-center gap-2">
                  <BatteryCharging className="h-4 w-4 text-green-500" />
                  <CardTitle>GSE & EV Charging Coordination</CardTitle>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {chargingPlan.map((item) => (
                    <div key={item.terminal} className="grid grid-cols-[1fr_auto] gap-3 border border-border rounded-md p-3">
                      <div>
                        <div className="font-semibold">{item.terminal}</div>
                        <div className="text-sm text-muted-foreground">{item.priority}</div>
                      </div>
                      <div className="text-right">
                        <div className="font-bold">{compact(item.shiftableKw)} kW</div>
                        <div className="text-xs text-muted-foreground">shiftable</div>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>

          <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
            <Card id="asset-health">
              <CardHeader>
                <div className="flex items-center gap-2">
                  <Factory className="h-4 w-4 text-blue-500" />
                  <CardTitle>HVAC Asset Health & Fault Detection</CardTitle>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {assetHealth.map((item) => (
                    <div key={item.terminal} className="border border-border rounded-md p-3">
                      <div className="flex items-center justify-between">
                        <div className="font-semibold">{item.terminal}</div>
                        <StatusBadge status={item.faultRisk} />
                      </div>
                      <div className="grid grid-cols-2 gap-3 mt-3 text-sm">
                        <div>
                          <div className="text-xs text-muted-foreground uppercase">HVAC Share</div>
                          <div className="font-bold">{Math.round(item.hvacShare * 100)}%</div>
                        </div>
                        <div>
                          <div className="text-xs text-muted-foreground uppercase">Signature</div>
                          <div className="font-bold">{item.comfort_status}</div>
                        </div>
                      </div>
                      <div className="text-sm text-muted-foreground mt-2">{item.probableCause}</div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            <Card id="comfort">
              <CardHeader>
                <div className="flex items-center gap-2">
                  <Activity className="h-4 w-4 text-red-500" />
                  <CardTitle>Comfort Compliance</CardTitle>
                </div>
              </CardHeader>
              <CardContent>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-border text-left text-muted-foreground">
                        <th className="py-2 pr-3">Terminal</th>
                        <th className="py-2 pr-3">Occupancy</th>
                        <th className="py-2 pr-3">Setpoint</th>
                        <th className="py-2 pr-3">Outdoor</th>
                        <th className="py-2">Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {terminals.map((terminal) => (
                        <tr key={terminal.terminal} className="border-b border-border/60">
                          <td className="py-3 pr-3 font-medium">{terminal.terminal}</td>
                          <td className="py-3 pr-3">{Math.round(terminal.occupancy_index * 100)}%</td>
                          <td className="py-3 pr-3">{terminal.indoor_setpoint_f.toFixed(0)}°F</td>
                          <td className="py-3 pr-3">{terminal.outdoor_temp_f.toFixed(1)}°F</td>
                          <td className="py-3"><StatusBadge status={terminal.comfort_status} /></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          </div>

          <div className="grid grid-cols-1 xl:grid-cols-3 gap-6" id="recommendations">
            <Card className="xl:col-span-2">
              <CardHeader>
                <div className="flex items-center gap-2">
                  <CloudSun className="h-4 w-4 text-yellow-500" />
                  <CardTitle>Terminal Actions</CardTitle>
                </div>
              </CardHeader>
              <CardContent>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-border text-left text-muted-foreground">
                        <th className="py-2 pr-3">Terminal</th>
                        <th className="py-2 pr-3">Load</th>
                        <th className="py-2 pr-3">HVAC</th>
                        <th className="py-2 pr-3">Occupancy</th>
                        <th className="py-2 pr-3">Comfort</th>
                        <th className="py-2">Action</th>
                      </tr>
                    </thead>
                    <tbody>
                      {terminals.map((terminal) => (
                        <tr key={terminal.terminal} className="border-b border-border/60">
                          <td className="py-3 pr-3 font-medium">{terminal.terminal}</td>
                          <td className="py-3 pr-3">{compact(terminal.current_load_kw)} kW</td>
                          <td className="py-3 pr-3">{compact(terminal.hvac_load_kw)} kW</td>
                          <td className="py-3 pr-3">{Math.round(terminal.occupancy_index * 100)}%</td>
                          <td className="py-3 pr-3"><StatusBadge status={terminal.comfort_status} /></td>
                          <td className="py-3 text-muted-foreground">{terminal.optimization_action}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <div className="flex items-center gap-2">
                  <Leaf className="h-4 w-4 text-green-500" />
                  <CardTitle>Recommendations</CardTitle>
                </div>
              </CardHeader>
              <CardContent className="space-y-3">
                {recommendations.length === 0 ? (
                  <div className="text-sm text-muted-foreground py-8 text-center">
                    No active energy recommendations
                  </div>
                ) : (
                  recommendations.slice(0, 5).map((rec, index) => (
                    <div key={`${rec.airport_code}-${rec.area}-${index}`} className="border border-border rounded-md p-3">
                      <div className="flex items-center justify-between gap-2 mb-2">
                        <div className="flex items-center gap-2">
                          <BatteryCharging className="h-4 w-4 text-green-500" />
                          <span className="text-sm font-semibold">{rec.action}</span>
                        </div>
                        <StatusBadge status={rec.priority} />
                      </div>
                      <div className="text-xs text-muted-foreground mb-1">
                        {rec.airport_code} · {rec.area}
                      </div>
                      <p className="text-sm text-muted-foreground">{rec.reason}</p>
                      <div className="text-xs text-green-500 mt-2">
                        Est. savings {money(rec.estimated_savings_usd)}
                      </div>
                    </div>
                  ))
                )}
              </CardContent>
            </Card>
          </div>
        </>
      )}
    </div>
  );
}
