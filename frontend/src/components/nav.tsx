"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useClock } from "./clock-context";
import { cn } from "@/lib/utils";
import {
  LayoutDashboard,
  Route,
  Layers,
  TrendingUp,
  AlertTriangle,
  Users,
  FlaskConical,
  BarChart3,
  Sun,
  Moon,
  Plane,
  Luggage,
  Radio,
  Wrench,
  ShoppingBag,
  Zap,
  Gauge,
  Factory,
  Leaf,
  BatteryCharging,
  Thermometer,
  DollarSign,
  Activity,
  ChevronRight,
} from "lucide-react";
import { useTheme } from "next-themes";

const modules = [
  { id: "queues", label: "Queue Mgmt", icon: Layers, active: true, href: "/" },
  { id: "flights", label: "Flight Ops", icon: Plane, active: false },
  { id: "baggage", label: "Baggage", icon: Luggage, active: false },
  { id: "comms", label: "Comms", icon: Radio, active: false },
  { id: "maintenance", label: "Maintenance", icon: Wrench, active: false },
  { id: "energy-management", label: "Energy", icon: Zap, active: true, href: "/energy-management" },
  { id: "retail", label: "Retail", icon: ShoppingBag, active: false },
];

const queuePages = [
  { href: "/", label: "Command Center", icon: LayoutDashboard },
  { href: "/journey", label: "Passenger Journey", icon: Route },
  { href: "/queues", label: "Queue Intelligence", icon: Layers },
  { href: "/forecast", label: "Forecast", icon: TrendingUp },
  { href: "/anomalies", label: "Anomalies", icon: AlertTriangle },
  { href: "/staffing", label: "Staffing", icon: Users },
  { href: "/simulator", label: "Simulator", icon: FlaskConical },
  { href: "/analytics", label: "Analytics", icon: BarChart3 },
];

const energyPages = [
  { href: "/energy-management#scenario-lab", label: "Scenario Lab", icon: Thermometer },
  { href: "/energy-management#load-forecast", label: "Load Forecast", icon: TrendingUp },
  { href: "/energy-management#demand-response", label: "Demand Response", icon: Gauge },
  { href: "/energy-management#carbon-renewables", label: "Carbon & Renewables", icon: Leaf },
  { href: "/energy-management#tariff-control", label: "Tariff Control", icon: DollarSign },
  { href: "/energy-management#asset-health", label: "Asset Health", icon: Factory },
  { href: "/energy-management#charging", label: "GSE Charging", icon: BatteryCharging },
  { href: "/energy-management#comfort", label: "Comfort Compliance", icon: Thermometer },
  { href: "/energy-management#recommendations", label: "Recommendations", icon: Activity },
];

export function TopBar() {
  const { resolvedTheme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);
  const pathname = usePathname();

  useEffect(() => {
    const frame = requestAnimationFrame(() => setMounted(true));
    return () => cancelAnimationFrame(frame);
  }, []);

  return (
    <header className="sticky top-0 z-50 border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="flex h-12 items-center px-4 gap-4">
        <Link href="/" className="flex items-center gap-2 font-bold text-foreground shrink-0">
          <Plane className="h-5 w-5 text-blue-500" />
          <span className="text-sm font-bold tracking-tight">Airport Ops Platform</span>
        </Link>

        <div className="h-5 w-px bg-border" />

        <nav className="flex items-center gap-1 overflow-x-auto flex-1">
          {modules.map((m) => {
            const content = (
              <>
                <m.icon className="h-3.5 w-3.5" />
                {m.label}
                {!m.active && <span className="text-[10px] opacity-50">Soon</span>}
              </>
            );
            const className = cn(
              "flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium whitespace-nowrap transition-colors",
              m.active && (m.id === "energy-management" ? pathname.startsWith("/energy-management") : !pathname.startsWith("/energy-management"))
                ? "bg-blue-500/10 text-blue-500 border border-blue-500/20 hover:bg-blue-500/15"
                : m.active
                  ? "text-muted-foreground hover:text-foreground hover:bg-muted"
                  : "text-muted-foreground/50 cursor-not-allowed"
            );
            return m.href ? (
              <Link key={m.id} href={m.href} className={className}>
                {content}
              </Link>
            ) : (
              <button key={m.id} className={className} disabled={!m.active}>
                {content}
              </button>
            );
          })}
        </nav>

        {mounted && (
          <button
            onClick={() => setTheme(resolvedTheme === "dark" ? "light" : "dark")}
            className="p-2 rounded-md hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
          >
            {resolvedTheme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
          </button>
        )}
      </div>
    </header>
  );
}

export function Sidebar() {
  const pathname = usePathname();
  const isEnergy = pathname.startsWith("/energy-management");
  const pages = isEnergy ? energyPages : queuePages;
  const title = isEnergy ? "Energy Management" : "Queue Management";
  const TitleIcon = isEnergy ? Zap : Layers;

  return (
    <aside className="w-56 shrink-0 border-r border-border bg-muted/30 flex flex-col">
      <div className="p-3 flex-1 overflow-y-auto">
        <div className="flex items-center gap-1.5 px-2 py-1.5 mb-2">
          <TitleIcon className="h-4 w-4 text-blue-500" />
          <span className="text-xs font-bold text-foreground uppercase tracking-wider">{title}</span>
        </div>
        <nav className="flex flex-col gap-0.5">
          {pages.map(({ href, label, icon: Icon }) => {
            const active = isEnergy ? false : pathname === href;
            return (
              <Link
                key={href}
                href={href}
                className={cn(
                  "flex items-center gap-2.5 px-3 py-2 rounded-md text-sm transition-colors group",
                  active
                    ? "bg-blue-500/10 text-blue-500 font-medium"
                    : "text-muted-foreground hover:text-foreground hover:bg-muted"
                )}
              >
                <Icon className="h-4 w-4 shrink-0" />
                <span className="flex-1">{label}</span>
                {active && <ChevronRight className="h-3 w-3 opacity-50" />}
              </Link>
            );
          })}
        </nav>
      </div>
      <ClockSelector />
    </aside>
  );
}

function ClockSelector() {
  const { demoNow, loading, setClock } = useClock();
  const [date, setDate] = useState("");
  const [time, setTime] = useState("");
  const [error, setError] = useState("");

  const handleSet = async () => {
    if (!date || !time) return;
    setError("");
    try {
      await setClock(`${date}T${time}:00`);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed");
    }
  };

  if (loading) return null;

  const displayDate = demoNow ? demoNow.slice(0, 10) : "";
  const displayTime = demoNow ? demoNow.slice(11, 16) : "";

  return (
    <div className="border-t border-border p-3">
      <div className="text-[10px] text-muted-foreground uppercase tracking-widest mb-2">
        Demo Clock
      </div>
      <div className="bg-card border border-border rounded-md px-3 py-2 mb-2">
        <div className="text-[10px] text-muted-foreground uppercase">Current</div>
        <div className="text-sm font-mono font-bold text-blue-500">
          {displayDate}
        </div>
        <div className="text-xs font-mono text-muted-foreground">
          {displayTime}
        </div>
      </div>
      <div className="flex gap-1.5 mb-1.5">
        <input
          type="date"
          value={date}
          onChange={(e) => setDate(e.target.value)}
          min="2020-02-15"
          max="2022-10-15"
          className="flex-1 bg-card border border-border rounded px-2 py-1 text-xs text-foreground"
        />
        <input
          type="time"
          value={time}
          onChange={(e) => setTime(e.target.value)}
          className="w-20 bg-card border border-border rounded px-2 py-1 text-xs text-foreground"
        />
      </div>
      <button
        onClick={handleSet}
        disabled={!date || !time}
        className="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-40 text-white text-xs font-medium py-1.5 rounded transition-colors"
      >
        Set Clock
      </button>
      {error && <div className="text-[10px] text-red-500 mt-1">{error}</div>}
      <div className="text-[10px] text-muted-foreground mt-1.5">
        Range: 2020-02-15 to 2022-10-15
      </div>
    </div>
  );
}
