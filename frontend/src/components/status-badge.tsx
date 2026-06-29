import { cn } from "@/lib/utils";

const colorMap: Record<string, string> = {
  OK: "bg-green-600 text-white",
  WARNING: "bg-yellow-600 text-white",
  BREACH: "bg-red-600 text-white",
  LOW: "bg-gray-500 text-white",
  MEDIUM: "bg-yellow-600 text-white",
  HIGH: "bg-red-600 text-white",
  EXCELLENT: "bg-green-600 text-white",
  GOOD: "bg-blue-500 text-white",
  FAIR: "bg-yellow-600 text-white",
  POOR: "bg-red-600 text-white",
  CRITICAL: "bg-red-700 text-white",
  MODERATE: "bg-blue-500 text-white",
};

export function StatusBadge({ status, className }: { status: string; className?: string }) {
  return (
    <span className={cn("px-2.5 py-1 rounded text-xs font-semibold tracking-wide", colorMap[status] || "bg-gray-500 text-white", className)}>
      {status}
    </span>
  );
}
