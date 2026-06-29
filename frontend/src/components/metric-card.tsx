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
      className={cn(
        "bg-card border border-border rounded-lg p-4 shadow-sm hover:shadow-md transition-shadow",
        className
      )}
      style={accentColor ? { borderLeftWidth: 3, borderLeftColor: accentColor } : undefined}
    >
      <div className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider mb-1.5">
        {label}
      </div>
      <div className="text-2xl font-bold text-foreground leading-none">{value}</div>
      {sublabel && (
        <div className="text-xs text-muted-foreground mt-1.5">{sublabel}</div>
      )}
    </div>
  );
}
