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
} from "lucide-react";
import { useTheme } from "next-themes";

const links = [
  { href: "/", label: "Command Center", icon: LayoutDashboard },
  { href: "/journey", label: "Passenger Journey", icon: Route },
  { href: "/queues", label: "Queue Intelligence", icon: Layers },
  { href: "/forecast", label: "Forecast", icon: TrendingUp },
  { href: "/anomalies", label: "Anomalies", icon: AlertTriangle },
  { href: "/staffing", label: "Staffing", icon: Users },
  { href: "/simulator", label: "Simulator", icon: FlaskConical },
  { href: "/analytics", label: "Analytics", icon: BarChart3 },
];

export function Nav() {
  const pathname = usePathname();
  const { theme, setTheme } = useTheme();

  return (
    <header className="sticky top-0 z-50 border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="flex h-14 items-center px-6 gap-6">
        <Link href="/" className="flex items-center gap-2 font-bold text-foreground">
          <LayoutDashboard className="h-5 w-5 text-blue-500" />
          <span className="hidden sm:inline">Airport Ops</span>
        </Link>

        <nav className="flex items-center gap-1 overflow-x-auto flex-1">
          {links.map(({ href, label, icon: Icon }) => {
            const active = pathname === href;
            return (
              <Link
                key={href}
                href={href}
                className={cn(
                  "flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm whitespace-nowrap transition-colors",
                  active
                    ? "bg-blue-500/10 text-blue-500 font-medium"
                    : "text-muted-foreground hover:text-foreground hover:bg-muted"
                )}
              >
                <Icon className="h-4 w-4" />
                <span className="hidden lg:inline">{label}</span>
              </Link>
            );
          })}
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
