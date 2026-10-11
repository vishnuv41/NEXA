"use client";

import { useEffect, useState } from "react";
import { cn } from "@/lib/utils";
import { useLiveEvents } from "@/hooks/useSSE";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "@/components/ui/Table";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardHeader } from "@/components/ui/Card";
import { useAppStore } from "@/hooks/useAppStore";
import { api } from "@/lib/api";
import {
  Search,
  Filter,
  Eye,
  X,
  ChevronDown,
  Download,
  Pause,
  Play,
} from "lucide-react";
import { formatTimestamp, getDecisionColor, getDecisionIcon, getRiskColor, truncate, getThreatTypeLabel } from "@/lib/utils";
import { DecisionEnum, ThreatTypeEnum, RequestEvent } from "@/types/api";
import { RequestDetailDrawer } from "@/components/ui/RequestDetailDrawer";

const DECISIONS: DecisionEnum[] = ["allow", "monitor", "rate_limit", "challenge", "block", "would_block"];
const ATTACK_TYPES: ThreatTypeEnum[] = ["benign", "sql_injection", "xss", "path_traversal", "command_injection", "other_malicious"];

export function LiveMonitorPage() {
  const liveEvents = useLiveEvents(200);
  const { clearLiveEvents, setLiveEvents } = useAppStore();
  const [selectedEvent, setSelectedEvent] = useState<RequestEvent | null>(null);
  const [search, setSearch] = useState("");
  const [decisionFilter, setDecisionFilter] = useState<DecisionEnum | "all">("all");
  const [attackFilter, setAttackFilter] = useState<ThreatTypeEnum | "all">("all");
  const [paused, setPaused] = useState(false);
  const [sortColumn, setSortColumn] = useState<string>("timestamp");
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("desc");

  useEffect(() => {
    if (liveEvents.length === 0) {
      api.events.getRecent(50).then((data: any) => {
        if (data && data.length > 0) {
          setLiveEvents(data as any);
        }
      }).catch((e: unknown) => console.error("Failed to load initial events:", e));
    }
  }, [liveEvents.length, setLiveEvents]);

  const filteredEvents = liveEvents
    .filter((e) => {
      if (search) {
        const s = search.toLowerCase();
        if (
          !e.path.toLowerCase().includes(s) &&
          !e.source_ip.includes(s) &&
          !e.request_id.includes(s) &&
          !(e.attack_type && e.attack_type.includes(s))
        ) {
          return false;
        }
      }
      if (decisionFilter !== "all" && e.decision !== decisionFilter) return false;
      if (attackFilter !== "all" && e.attack_type !== attackFilter) return false;
      return true;
    })
    .sort((a, b) => {
      const rec = (a as unknown) as Record<string, unknown>;
      const rec2 = (b as unknown) as Record<string, unknown>;
      const aVal = rec[sortColumn];
      const bVal = rec2[sortColumn];
      if (aVal == null && bVal == null) return 0;
      if (aVal == null) return 1;
      if (bVal == null) return -1;
      const cmp = (aVal as any) < (bVal as any) ? -1 : (aVal as any) > (bVal as any) ? 1 : 0;
      return sortDirection === "asc" ? cmp : -cmp;
    });

  useEffect(() => {
    if (!paused && liveEvents.length > 0) {
      // Auto-scroll handled by table
    }
  }, [liveEvents.length, paused]);

  const handleSort = (column: string) => {
    if (sortColumn === column) {
      setSortDirection(sortDirection === "asc" ? "desc" : "asc");
    } else {
      setSortColumn(column);
      setSortDirection("desc");
    }
  };

  const exportEvents = () => {
    const csv = [
      ["Time", "Method", "Path", "Source IP", "Session", "Risk", "Attack Type", "Decision", "Latency"],
      ...filteredEvents.map((e) => [
        formatTimestamp(e.timestamp),
        e.method,
        e.path,
        e.source_ip,
        e.session_id || "",
        (((e.final_risk_score ?? e.risk_score ?? 0) * 100).toFixed(1)) + "%",
        e.attack_type || "benign",
        e.decision,
        e.latency_ms + "ms",
      ]),
    ].map((row) => row.map((v) => `"${v}"`).join(",")).join("\n");

    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `waf-events-${Date.now()}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-text">Live Monitor</h1>
          <p className="text-text-secondary text-sm">Real-time request inspection and threat detection</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={exportEvents}>
            <Download className="w-4 h-4" />
            Export CSV
          </Button>
          <Button variant="outline" size="sm" onClick={() => setPaused(!paused)}>
            {paused ? <Play className="w-4 h-4" /> : <Pause className="w-4 h-4" />}
            {paused ? "Resume" : "Pause"}
          </Button>
          <Button variant="secondary" size="sm" onClick={clearLiveEvents}>
            <X className="w-4 h-4" />
            Clear
          </Button>
        </div>
      </div>

      <Card>
        <CardContent className="p-4">
          <div className="flex flex-col sm:flex-row gap-4 mb-4">
            <div className="relative flex-1 max-w-md">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted" />
              <input
                type="text"
                placeholder="Search path, IP, request ID, attack type..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="input pl-10"
              />
            </div>
            <div className="flex gap-2">
              <select
                value={decisionFilter}
                onChange={(e) => setDecisionFilter(e.target.value as DecisionEnum | "all")}
                className="input w-40"
              >
                <option value="all">All Decisions</option>
                {DECISIONS.map((d) => (
                  <option key={d} value={d}>{d}</option>
                ))}
              </select>
              <select
                value={attackFilter}
                onChange={(e) => setAttackFilter(e.target.value as ThreatTypeEnum | "all")}
                className="input w-40"
              >
                <option value="all">All Attack Types</option>
                {ATTACK_TYPES.map((a) => (
                  <option key={a} value={a}>{getThreatTypeLabel(a)}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  {[
                    { key: "timestamp", label: "Time" },
                    { key: "method", label: "Method" },
                    { key: "path", label: "Endpoint" },
                    { key: "source_ip", label: "Source IP" },
                    { key: "session_id", label: "Session" },
                    { key: "final_risk_score", label: "Risk" },
                    { key: "attack_type", label: "Attack Type" },
                    { key: "decision", label: "Decision" },
                    { key: "latency_ms", label: "Latency" },
                  ].map((col) => (
                    <TableHead
                      key={col.key}
                      onClick={() => handleSort(col.key)}
                      className="cursor-pointer select-none"
                    >
                      <div className="flex items-center gap-1">
                        {col.label}
                        {sortColumn === col.key && (
                          <ChevronDown className={cn("w-3 h-3", sortDirection === "asc" ? "rotate-180" : "")} />
                        )}
                      </div>
                    </TableHead>
                  ))}
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredEvents.length > 0 ? (
                  filteredEvents.map((event, index) => (
                    <TableRow key={`${event.request_id}-${index}`} onClick={() => setSelectedEvent(event as any)}>
                      <TableCell className="text-text-muted font-mono">{formatTimestamp(event.timestamp)}</TableCell>
                      <TableCell>
                        <span className="font-mono text-text bg-surface-hover px-1.5 py-0.5 rounded">
                          {event.method}
                        </span>
                      </TableCell>
                      <TableCell className="font-mono truncate max-w-md" title={event.path}>{event.path}</TableCell>
                      <TableCell className="text-text-secondary">{event.source_ip}</TableCell>
                      <TableCell>
                        {event.session_id ? (
                          <span className="font-mono text-xs text-text-secondary">{truncate(event.session_id, 12)}</span>
                        ) : (
                          <span className="text-text-muted">—</span>
                        )}
                      </TableCell>
                      <TableCell>
                        <span className={cn("font-mono font-medium", getRiskColor(event.final_risk_score ?? event.risk_score ?? 0))}>
                          {(((event.final_risk_score ?? event.risk_score ?? 0) * 100).toFixed(1))}%
                        </span>
                      </TableCell>
                      <TableCell>
                        {event.attack_type && event.attack_type !== "benign" ? (
                          <Badge variant="danger" className="text-xs">{getThreatTypeLabel(event.attack_type)}</Badge>
                        ) : (
                          <Badge variant="success" className="text-xs">Benign</Badge>
                        )}
                      </TableCell>
                      <TableCell>
                        <Badge variant={getDecisionColor(event.decision).includes("danger") ? "danger" : getDecisionColor(event.decision).includes("warning") ? "warning" : getDecisionColor(event.decision).includes("info") ? "info" : "success"}>
                          {event.decision}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-text-muted font-mono">{event.latency_ms}ms</TableCell>
                      <TableCell>
                        <Button variant="ghost" size="icon" onClick={(e) => { e.stopPropagation(); setSelectedEvent(event as any); }}>
                          <Eye className="w-4 h-4" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))
                ) : (
                  <TableRow>
                    <TableCell colSpan={10} className="py-8 text-center text-text-muted">
                      {paused ? "Live feed paused. Click Resume to continue." : "No events yet. Generate traffic to see live requests."}
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </div>

          <div className="mt-4 flex items-center justify-between text-sm text-text-secondary">
            <span>Showing {filteredEvents.length} of {liveEvents.length} events</span>
            <span className="flex items-center gap-1">
              <span className={cn("w-2 h-2 rounded-full", useAppStore.getState().isConnected ? "bg-success" : "bg-danger")} />
              {useAppStore.getState().isConnected ? "Live" : "Disconnected"}
            </span>
          </div>
        </CardContent>
      </Card>

      {selectedEvent && (
        <RequestDetailDrawer
          event={selectedEvent}
          onClose={() => setSelectedEvent(null)}
        />
      )}
    </div>
  );
}