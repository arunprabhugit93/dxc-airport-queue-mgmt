"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
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
  ChevronRight,
} from "lucide-react";
import { useTheme } from "next-themes";

const modules = [
  { id: "queues", label: "Queue Mgmt", icon: Layers, active: true },
  { id: "flights", label: "Flight Ops", icon: Plane, active: false },
  { id: "baggage", label: "Baggage", icon: Luggage, active: false },
  { id: "comms", label: "Comms", icon: Radio, active: false },
  { id: "maintenance", label: "Maintenance", icon: Wrench, active: false },
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

export function TopBar() {
  const { theme, setTheme } = useTheme();

  return (
    <header className="sticky top-0 z-50 border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="flex h-12 items-center px-4 gap-4">
        <Link href="/" className="flex items-center gap-2 font-bold text-foreground shrink-0">
          <Plane className="h-5 w-5 text-blue-500" />
          <span className="text-sm font-bold tracking-tight">Airport Ops Platform</span>
        </Link>

        <div className="h-5 w-px bg-border" />

        <nav className="flex items-center gap-1 overflow-x-auto flex-1">
          {modules.map((m) => (
            <button
              key={m.id}
              className={cn(
                "flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium whitespace-nowrap transition-colors",
                m.active
                  ? "bg-blue-500/10 text-blue-500 border border-blue-500/20"
                  : "text-muted-foreground/50 cursor-not-allowed"
              )}
              disabled={!m.active}
            >
              <m.icon className="h-3.5 w-3.5" />
              {m.label}
              {!m.active && <span className="text-[10px] opacity-50">Soon</span>}
            </button>
          ))}
        </nav>

        <button
          onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
          className="p-2 rounded-md hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
        >
          {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
        </button>
      </div>
    </header>
  );
}

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-56 shrink-0 border-r border-border bg-muted/30 overflow-y-auto">
      <div className="p-3">
        <div className="flex items-center gap-1.5 px-2 py-1.5 mb-2">
          <Layers className="h-4 w-4 text-blue-500" />
          <span className="text-xs font-bold text-foreground uppercase tracking-wider">Queue Management</span>
        </div>
        <nav className="flex flex-col gap-0.5">
          {queuePages.map(({ href, label, icon: Icon }) => {
            const active = pathname === href;
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
    </aside>
  );
}
