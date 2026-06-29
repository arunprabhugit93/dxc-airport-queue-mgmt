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
  EnergyScenarioCase,
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
} from "lucide-react";

function money(value: number): string {
  return `$${Math.round(value).toLocaleString()}`;
}

function compact(value: number): string {
  return Math.round(value).toLocaleString();
}

function scenarioStatus(outdoor: number, indoor: number, setpoint: number) {
  const deltaToIndoor = outdoor - indoor;
  const deltaToSetpoint = outdoor - setpoint;

  if (outdoor <= indoor - 4) {
    return {
      mode: "FREE_COOLING",
      priority: "LOW",
      label: "Outdoor cooler than indoor",
      action: "Decrease compressor load and use outside-air economizer",
      detail: "Bring cooler outdoor air into the terminal, reduce chilled-water demand, and keep fans active.",
      hvacFactor: 0.58,
    };
  }
  if (deltaToSetpoint <= 3) {
    return {
      mode: "BALANCED",
      priority: "LOW",
      label: "Near comfort band",
      action: "Hold setpoint and trim fan speed",
      detail: "Cooling demand is modest; keep comfort stable and avoid unnecessary compressor cycling.",
      hvacFactor: 0.82,
    };
  }
  if (outdoor >= 95 || deltaToIndoor >= 18) {
    return {
      mode: "EXTREME_COOLING",
      priority: "HIGH",
      label: "Very hot outdoor condition",
      action: "Increase cooling capacity and pre-cool before peak tariff",
      detail: "Passenger comfort risk is high; stage chillers, defer noncritical charging, and avoid simultaneous peaks.",
      hvacFactor: 1.34,
    };
  }
  return {
    mode: "ACTIVE_COOLING",
    priority: "MEDIUM",
    label: "Hot outdoor condition",
    action: "Increase cooling moderately and monitor demand response options",
    detail: "HVAC load rises with outdoor temperature and passenger density; shift flexible loads if tariff is high.",
    hvacFactor: 1.08,
  };
}

export default function EnergyManagementPage() {
  const { demoNow } = useClock();
  const [airport, setAirport] = useState(AIRPORT_CODES[0]);
  const [overview, setOverview] = useState<EnergyAirportSummary[]>([]);
  const [terminals, setTerminals] = useState<EnergyTerminalStatus[]>([]);
  const [profile, setProfile] = useState<EnergyTemperaturePoint[]>([]);
  const [recommendations, setRecommendations] = useState<EnergyRecommendation[]>([]);
  const [scenarioCases, setScenarioCases] = useState<EnergyScenarioCase[]>([]);
  const [scenarioWindowHours, setScenarioWindowHours] = useState(8);
  const [scenarioOutdoor, setScenarioOutdoor] = useState(86);
  const [scenarioIndoor, setScenarioIndoor] = useState(74);
  const [scenarioSetpoint, setScenarioSetpoint] = useState(72);
  const [scenarioOccupancy, setScenarioOccupancy] = useState(68);
  const [tariff, setTariff] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const [overviewRes, terminalsRes, profileRes, recRes, casesRes] = await Promise.all([
          api.getEnergyOverview(),
          api.getEnergyTerminals(airport),
          api.getEnergyTemperatureProfile(airport),
          api.getEnergyRecommendations(airport),
          api.getEnergyScenarioCases(),
        ]);
        if (cancelled) return;
        setOverview(overviewRes.airports);
        setTariff(overviewRes.tariff_usd_per_kwh);
        setTerminals(terminalsRes.terminals);
        setProfile(profileRes.points);
        setRecommendations(recRes.recommendations);
        setScenarioCases(casesRes.cases);
        const activeAirport = overviewRes.airports.find((item) => item.airport_code === airport);
        if (activeAirport) {
          setScenarioOutdoor(Math.round(activeAirport.outdoor_temp_f));
          setScenarioSetpoint(Math.round(activeAirport.indoor_setpoint_f));
          setScenarioIndoor(Math.round(activeAirport.indoor_setpoint_f + 2));
        }
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
  const scenario = scenarioStatus(scenarioOutdoor, scenarioIndoor, scenarioSetpoint);
  const baseHvacKw = selectedAirport?.hvac_load_kw ?? 0;
  const occupancyFactor = 0.72 + (scenarioOccupancy / 100) * 0.56;
  const heatLift = Math.max(scenarioOutdoor - scenarioSetpoint, 0) * 0.018;
  const scenarioHvacKw = baseHvacKw * scenario.hvacFactor * occupancyFactor * (1 + heatLift);
  const baselineScenarioKw = baseHvacKw * (0.72 + 0.68 * 0.56);
  const scenarioDeltaKw = scenarioHvacKw - baselineScenarioKw;
  const scenarioCostDelta = scenarioDeltaKw * Math.max(tariff, 0.14) * scenarioWindowHours;
  const scenarioCarbonDelta = scenarioDeltaKw * 0.38 * scenarioWindowHours;

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

          <Card id="scenario-lab">
            <CardHeader>
              <div className="flex items-center gap-2">
                <Thermometer className="h-4 w-4 text-red-500" />
                <CardTitle>Live Temperature Scenario Lab</CardTitle>
              </div>
            </CardHeader>
            <CardContent className="space-y-5">
              <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
                <div className="border border-border rounded-md p-4">
                  <div className="flex items-center justify-between text-sm mb-3">
                    <span className="text-muted-foreground">Outdoor temp</span>
                    <span className="font-mono">{scenarioOutdoor}°F</span>
                  </div>
                  <input
                    type="range"
                    min={35}
                    max={110}
                    step={1}
                    value={scenarioOutdoor}
                    onChange={(event) => setScenarioOutdoor(Number(event.target.value))}
                    className="w-full"
                  />
                </div>
                <div className="border border-border rounded-md p-4">
                  <div className="flex items-center justify-between text-sm mb-3">
                    <span className="text-muted-foreground">Indoor temp</span>
                    <span className="font-mono">{scenarioIndoor}°F</span>
                  </div>
                  <input
                    type="range"
                    min={60}
                    max={88}
                    step={1}
                    value={scenarioIndoor}
                    onChange={(event) => setScenarioIndoor(Number(event.target.value))}
                    className="w-full"
                  />
                </div>
                <div className="border border-border rounded-md p-4">
                  <div className="flex items-center justify-between text-sm mb-3">
                    <span className="text-muted-foreground">Target setpoint</span>
                    <span className="font-mono">{scenarioSetpoint}°F</span>
                  </div>
                  <input
                    type="range"
                    min={68}
                    max={80}
                    step={1}
                    value={scenarioSetpoint}
                    onChange={(event) => setScenarioSetpoint(Number(event.target.value))}
                    className="w-full"
                  />
                </div>
                <div className="border border-border rounded-md p-4">
                  <div className="flex items-center justify-between text-sm mb-3">
                    <span className="text-muted-foreground">Occupancy</span>
                    <span className="font-mono">{scenarioOccupancy}%</span>
                  </div>
                  <input
                    type="range"
                    min={10}
                    max={100}
                    step={5}
                    value={scenarioOccupancy}
                    onChange={(event) => setScenarioOccupancy(Number(event.target.value))}
                    className="w-full"
                  />
                </div>
                <div className="border border-border rounded-md p-4">
                  <div className="flex items-center justify-between text-sm mb-3">
                    <span className="text-muted-foreground">Analysis window</span>
                    <span className="font-mono">{scenarioWindowHours}h</span>
                  </div>
                  <input
                    type="range"
                    min={1}
                    max={24}
                    step={1}
                    value={scenarioWindowHours}
                    onChange={(event) => setScenarioWindowHours(Number(event.target.value))}
                    className="w-full"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 xl:grid-cols-[1.2fr_1fr] gap-4">
                <div className="border border-border rounded-md p-4">
                  <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
                    <div>
                      <div className="text-xs text-muted-foreground uppercase tracking-wider">Detected condition</div>
                      <div className="text-xl font-bold mt-1">{scenario.label}</div>
                    </div>
                    <StatusBadge status={scenario.priority} />
                  </div>
                  <div className="text-sm font-semibold">{scenario.action}</div>
                  <p className="text-sm text-muted-foreground mt-2">{scenario.detail}</p>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mt-4">
                    <div className="border border-border rounded-md p-3">
                      <div className="text-xs text-muted-foreground uppercase">Scenario HVAC</div>
                      <div className="text-lg font-bold mt-1">{compact(scenarioHvacKw)} kW</div>
                    </div>
                    <div className="border border-border rounded-md p-3">
                      <div className="text-xs text-muted-foreground uppercase">Cost impact</div>
                      <div className={`text-lg font-bold mt-1 ${scenarioCostDelta > 0 ? "text-red-500" : "text-green-500"}`}>
                        {scenarioCostDelta > 0 ? "+" : ""}{money(scenarioCostDelta)}
                      </div>
                    </div>
                    <div className="border border-border rounded-md p-3">
                      <div className="text-xs text-muted-foreground uppercase">Carbon impact</div>
                      <div className={`text-lg font-bold mt-1 ${scenarioCarbonDelta > 0 ? "text-red-500" : "text-green-500"}`}>
                        {scenarioCarbonDelta > 0 ? "+" : ""}{compact(scenarioCarbonDelta)} kg
                      </div>
                    </div>
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {scenarioCases.map((item) => (
                    <div key={item.title} className="border border-border rounded-md p-3">
                      <div className="flex items-center justify-between gap-2">
                        <div className="text-sm font-semibold">{item.title}</div>
                        <StatusBadge status={item.priority} />
                      </div>
                      <div className="text-xs text-blue-500 mt-1">{item.condition}</div>
                      <div className="text-sm mt-2">{item.decision}</div>
                      <div className="text-xs text-muted-foreground mt-1">{item.impact}</div>
                    </div>
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>

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
