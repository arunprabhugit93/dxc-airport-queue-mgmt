import { cn } from "@/lib/utils";

interface MetricCardProps {
  label: string;
  value: string | number;
  sublabel?: string;
  accentColor?: string;
  className?: string;
}

export function MetricCard({ label, value, sublabel, accentColor, className }: MetricCardProps) {
  return (
    <div
      className={cn("bg-card border border-border rounded-lg p-5", className)}
      style={accentColor ? { borderLeftWidth: 4, borderLeftColor: accentColor } : undefined}
    >
      <div className="text-xs text-muted-foreground uppercase tracking-wider mb-2">{label}</div>
      <div className="text-3xl font-bold text-foreground">{value}</div>
      {sublabel && <div className="text-xs text-muted-foreground mt-1">{sublabel}</div>}
    </div>
  );
}
