"use client";

import { useEffect, useState } from "react";
import { useClock } from "@/components/clock-context";
import { api, AIRPORT_CODES, SLA_COLORS } from "@/lib/api";
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
  AlertTriangle,
  CheckCircle2,
  Clock,
  Users,
  TrendingUp,
  Calendar,
  Eye,
} from "lucide-react";

interface ShiftEvent {
  time: string;
  event_type: string;
  description: string;
  severity: string | null;
}

interface ShiftHandoff {
  airport_code: string;
  shift_start: string;
  shift_end: string;
  summary: string;
  peak_wait_min: number;
  avg_wait_min: number;
  total_pax: number;
  anomalies_during_shift: number;
  sla_breaches: number;
  key_events: ShiftEvent[];
  next_shift_outlook: string;
}

function fmtTime(iso: string) {
  return new Date(iso).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });
}

function fmtDate(iso: string) {
  return new Date(iso).toLocaleDateString([], {
    weekday: "short",
    month: "short",
    day: "numeric",
  });
}

function severityColor(s: string | null): string {
  if (s === "HIGH") return "text-red-500";
  if (s === "MEDIUM") return "text-yellow-500";
  return "text-muted-foreground";
}

function severityDot(s: string | null): string {
  if (s === "HIGH") return "bg-red-500";
  if (s === "MEDIUM") return "bg-yellow-500";
  return "bg-blue-500";
}

export default function ShiftHandoffPage() {
  const { demoNow } = useClock();
  const [airport, setAirport] = useState("All");
  const [shiftHours, setShiftHours] = useState(8);
  const [handoffs, setHandoffs] = useState<ShiftHandoff[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const res = await api.getShiftHandoff(
          airport === "All" ? undefined : airport,
        );
        if (!cancelled) setHandoffs(res.handoffs);
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
  }, [demoNow, airport, shiftHours]);

  const anyBreaches = handoffs.some((h) => h.sla_breaches > 0);
  const totalPaxAcross = handoffs.reduce((s, h) => s + h.total_pax, 0);
  const avgWaitAcross =
    handoffs.length > 0
      ? handoffs.reduce((s, h) => s + h.avg_wait_min, 0) / handoffs.length
      : 0;

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
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold">Shift Handoff</h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Auto-generated briefing for the outgoing shift — what happened, what
            to watch, what's next.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Select
            value={String(shiftHours)}
            onValueChange={(v) => setShiftHours(Number(v))}
          >
            <SelectTrigger className="w-32">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="4">4-hr shift</SelectItem>
              <SelectItem value="8">8-hr shift</SelectItem>
              <SelectItem value="12">12-hr shift</SelectItem>
            </SelectContent>
          </Select>
          <Select
            value={airport}
            onValueChange={(v) => v && setAirport(v)}
          >
            <SelectTrigger className="w-40">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="All">All Airports</SelectItem>
              {AIRPORT_CODES.map((code) => (
                <SelectItem key={code} value={code}>
                  {code}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {loading ? (
        <div className="text-muted-foreground py-20 text-center">
          Loading…
        </div>
      ) : (
        <>
          {/* Network summary strip */}
          {handoffs.length > 0 && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <Card>
                <CardContent className="py-4">
                  <div className="text-xs text-muted-foreground mb-1">
                    Airports Covered
                  </div>
                  <div className="text-2xl font-bold">{handoffs.length}</div>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="py-4">
                  <div className="text-xs text-muted-foreground mb-1">
                    Total Pax This Shift
                  </div>
                  <div className="text-2xl font-bold">
                    {totalPaxAcross.toLocaleString()}
                  </div>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="py-4">
                  <div className="text-xs text-muted-foreground mb-1">
                    Avg Wait (Network)
                  </div>
                  <div
                    className="text-2xl font-bold"
                    style={{
                      color:
                        avgWaitAcross >= 10
                          ? SLA_COLORS.BREACH
                          : avgWaitAcross >= 8
                            ? SLA_COLORS.WARNING
                            : undefined,
                    }}
                  >
                    {avgWaitAcross.toFixed(1)} min
                  </div>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="py-4">
                  <div className="text-xs text-muted-foreground mb-1">
                    SLA Status
                  </div>
                  <div>
                    {anyBreaches ? (
                      <StatusBadge status="BREACH" />
                    ) : (
                      <StatusBadge status="OK" />
                    )}
                  </div>
                </CardContent>
              </Card>
            </div>
          )}

          {/* Per-airport handoff cards */}
          {handoffs.length === 0 ? (
            <Card>
              <CardContent className="py-10 text-center text-muted-foreground">
                No handoff data available for this selection.
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-4">
              {handoffs.map((h) => {
                const statusColor =
                  h.sla_breaches > 0
                    ? "border-red-500/40 bg-red-500/5"
                    : h.avg_wait_min >= 8
                      ? "border-yellow-500/40 bg-yellow-500/5"
                      : "border-green-500/20";

                return (
                  <Card key={h.airport_code} className={`border ${statusColor}`}>
                    <CardHeader>
                      <div className="flex items-start justify-between gap-4 flex-wrap">
                        <div>
                          <div className="flex items-center gap-3 mb-1">
                            <CardTitle className="text-xl">
                              {h.airport_code}
                            </CardTitle>
                            {h.sla_breaches > 0 ? (
                              <StatusBadge status="BREACH" />
                            ) : h.avg_wait_min >= 8 ? (
                              <StatusBadge status="WARNING" />
                            ) : (
                              <StatusBadge status="OK" />
                            )}
                          </div>
                          <p className="text-xs text-muted-foreground flex items-center gap-1.5">
                            <Calendar className="h-3 w-3" />
                            {fmtDate(h.shift_start)} · {fmtTime(h.shift_start)}{" "}
                            → {fmtTime(h.shift_end)}
                          </p>
                        </div>
                        <div className="grid grid-cols-4 gap-4 text-center text-sm shrink-0">
                          <div>
                            <div className="text-xs text-muted-foreground mb-0.5 flex items-center gap-1 justify-center">
                              <Users className="h-3 w-3" />
                              Pax
                            </div>
                            <div className="font-bold">
                              {h.total_pax.toLocaleString()}
                            </div>
                          </div>
                          <div>
                            <div className="text-xs text-muted-foreground mb-0.5 flex items-center gap-1 justify-center">
                              <Clock className="h-3 w-3" />
                              Avg Wait
                            </div>
                            <div
                              className="font-bold"
                              style={{
                                color:
                                  h.avg_wait_min >= 10
                                    ? SLA_COLORS.BREACH
                                    : h.avg_wait_min >= 8
                                      ? SLA_COLORS.WARNING
                                      : undefined,
                              }}
                            >
                              {h.avg_wait_min.toFixed(1)} m
                            </div>
                          </div>
                          <div>
                            <div className="text-xs text-muted-foreground mb-0.5 flex items-center gap-1 justify-center">
                              <TrendingUp className="h-3 w-3" />
                              Peak
                            </div>
                            <div
                              className="font-bold"
                              style={{
                                color:
                                  h.peak_wait_min >= 10
                                    ? SLA_COLORS.BREACH
                                    : undefined,
                              }}
                            >
                              {h.peak_wait_min.toFixed(1)} m
                            </div>
                          </div>
                          <div>
                            <div className="text-xs text-muted-foreground mb-0.5 flex items-center gap-1 justify-center">
                              <AlertTriangle className="h-3 w-3" />
                              Breaches
                            </div>
                            <div
                              className="font-bold"
                              style={{
                                color:
                                  h.sla_breaches > 0
                                    ? SLA_COLORS.BREACH
                                    : undefined,
                              }}
                            >
                              {h.sla_breaches}
                            </div>
                          </div>
                        </div>
                      </div>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      {/* Shift Summary */}
                      <p className="text-sm text-muted-foreground leading-relaxed border-l-2 border-border pl-3">
                        {h.summary}
                      </p>

                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {/* Key Events Timeline */}
                        {h.key_events.length > 0 && (
                          <div>
                            <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">
                              Key Events During Shift
                            </h3>
                            <div className="space-y-2">
                              {h.key_events.slice(0, 6).map((ev, i) => (
                                <div key={i} className="flex items-start gap-3">
                                  <div className="flex flex-col items-center shrink-0 mt-1">
                                    <span
                                      className={`w-2 h-2 rounded-full ${severityDot(ev.severity)}`}
                                    />
                                    {i < h.key_events.slice(0, 6).length - 1 && (
                                      <div className="w-px h-4 bg-border mt-0.5" />
                                    )}
                                  </div>
                                  <div className="flex-1 min-w-0 pb-1">
                                    <div className="flex items-center gap-2">
                                      <span className="text-xs font-mono text-muted-foreground">
                                        {fmtTime(ev.time)}
                                      </span>
                                      <span
                                        className={`text-xs font-semibold uppercase ${severityColor(ev.severity)}`}
                                      >
                                        {ev.event_type}
                                      </span>
                                    </div>
                                    <p className="text-xs text-muted-foreground mt-0.5 leading-relaxed">
                                      {ev.description}
                                    </p>
                                  </div>
                                </div>
                              ))}
                              {h.key_events.length > 6 && (
                                <p className="text-xs text-muted-foreground pl-5">
                                  +{h.key_events.length - 6} more events
                                </p>
                              )}
                            </div>
                          </div>
                        )}
                        {h.key_events.length === 0 && (
                          <div>
                            <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">
                              Key Events
                            </h3>
                            <div className="flex items-center gap-2 text-sm text-muted-foreground">
                              <CheckCircle2 className="h-4 w-4 text-green-500" />
                              No notable events during this shift.
                            </div>
                          </div>
                        )}

                        {/* Next Shift Outlook */}
                        <div>
                          <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3 flex items-center gap-1.5">
                            <Eye className="h-3 w-3" />
                            Next Shift Outlook
                          </h3>
                          <div className="bg-muted/40 rounded-lg p-3">
                            <p className="text-sm leading-relaxed">
                              {h.next_shift_outlook}
                            </p>
                          </div>
                          <div className="mt-3 grid grid-cols-2 gap-2 text-xs text-muted-foreground">
                            <div className="bg-card border border-border rounded p-2">
                              <div className="font-semibold text-foreground mb-0.5">
                                Anomalies This Shift
                              </div>
                              <div
                                className={
                                  h.anomalies_during_shift > 0
                                    ? "text-yellow-500"
                                    : ""
                                }
                              >
                                {h.anomalies_during_shift > 0
                                  ? `${h.anomalies_during_shift} detected`
                                  : "None detected"}
                              </div>
                            </div>
                            <div className="bg-card border border-border rounded p-2">
                              <div className="font-semibold text-foreground mb-0.5">
                                SLA Compliance
                              </div>
                              <div
                                style={{
                                  color:
                                    h.sla_breaches > 0
                                      ? SLA_COLORS.BREACH
                                      : SLA_COLORS.OK,
                                }}
                              >
                                {h.sla_breaches === 0
                                  ? "100% within SLA"
                                  : `${h.sla_breaches} breach${h.sla_breaches > 1 ? "es" : ""}`}
                              </div>
                            </div>
                          </div>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          )}
        </>
      )}
    </div>
  );
}
