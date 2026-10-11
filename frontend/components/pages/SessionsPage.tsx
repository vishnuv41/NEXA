"use client";

import { useEffect, useState } from "react";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader } from "@/components/ui/Card";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "@/components/ui/Table";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { useAppStore } from "@/hooks/useAppStore";
import {
  Search,
  GitBranch,
  ArrowUpDown,
  Clock,
  TrendingUp,
  Download,
  RefreshCw,
  X,
} from "lucide-react";
import { formatTimestamp, formatDateTime, getRiskColor, getRiskBg, truncate } from "@/lib/utils";
import { Session } from "@/types/api";

export function SessionsPage() {
  const { setSessions } = useAppStore();
  const [sessions, setSessionsLocal] = useState<Session[]>([]);
  const [selectedSession, setSelectedSession] = useState<Session | null>(null);
  const [search, setSearch] = useState("");
  const [minRisk, setMinRisk] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadSessions();
    const interval = setInterval(loadSessions, 30000);
    return () => clearInterval(interval);
  }, []);

  const loadSessions = async (riskThreshold = minRisk) => {
    try {
      const data = await api.events.getSessions(100, riskThreshold);
      setSessionsLocal(data);
      setSessions(data as any);
      setLoading(false);
    } catch (e) {
      console.error("Failed to load sessions:", e);
      setLoading(false);
    }
  };

  const filteredSessions = sessions.filter((s) => {
    const risk = s.risk_score ?? 0;
    if (risk < minRisk) return false;
    if (search) {
      const s_lower = search.toLowerCase();
      if (
        !s.session_key.toLowerCase().includes(s_lower) &&
        !s.source_ip.toLowerCase().includes(s_lower) &&
        !(s.user_identifier && s.user_identifier.toLowerCase().includes(s_lower))
      ) return false;
    }
    return true;
  });

  const handleViewSession = async (session: Session) => {
    try {
      const detail = await api.events.getSession(session.session_key);
      setSelectedSession(detail);
    } catch (e) {
      console.error("Failed to load session detail:", e);
    }
  };

  const exportSessions = () => {
    const csv = [
      ["Session ID", "Source IP", "User", "Started", "Last Seen", "Requests", "Risk Score", "Anomaly Score", "Endpoints", "Status"],
      ...filteredSessions.map((s) => [
        s.session_key,
        s.source_ip,
        s.user_identifier || "",
        formatDateTime(s.started_at),
        formatDateTime(s.last_seen_at),
        s.request_count.toString(),
        (s.risk_score * 100).toFixed(1) + "%",
        (s.anomaly_score * 100).toFixed(1) + "%",
        s.endpoint_count.toString(),
        s.current_state || "active",
      ]),
    ].map((row) => row.map((v) => `"${v}"`).join(",")).join("\n");

    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `sessions-${Date.now()}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-text">Sessions</h1>
          <p className="text-text-secondary text-sm">Track user behavior across request sequences</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={() => loadSessions()}>
            <RefreshCw className="w-4 h-4" />
            Refresh
          </Button>
          <Button variant="outline" size="sm" onClick={exportSessions}>
            <Download className="w-4 h-4" />
            Export
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
                placeholder="Search session ID or IP..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="input pl-10"
              />
            </div>
            <div className="flex items-center gap-2">
              <label className="text-sm text-text-secondary">Min Risk:</label>
              <input
                type="range"
                min="0"
                max="100"
                value={minRisk * 100}
                onChange={(e) => setMinRisk(Number(e.target.value) / 100)}
                className="w-40 h-2 bg-surface-hover rounded-lg appearance-none accent-primary"
              />
              <span className="text-sm font-mono text-text-secondary w-10">{Math.round(minRisk * 100)}%</span>
            </div>
          </div>

          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Session ID</TableHead>
                  <TableHead>Source IP</TableHead>
                  <TableHead>User</TableHead>
                  <TableHead>Started</TableHead>
                  <TableHead>Last Seen</TableHead>
                  <TableHead className="text-right">Requests</TableHead>
                  <TableHead>Risk Score</TableHead>
                  <TableHead>Anomaly</TableHead>
                  <TableHead className="text-right">Endpoints</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredSessions.length > 0 ? (
                  filteredSessions.map((session, i) => (
                    <TableRow key={i} onClick={() => handleViewSession(session)} className="cursor-pointer">
                      <TableCell className="font-mono text-text truncate max-w-xs" title={session.session_key}>
                        {truncate(session.session_key, 20)}
                      </TableCell>
                      <TableCell className="text-text-secondary">{session.source_ip}</TableCell>
                      <TableCell className="text-text-secondary truncate max-w-xs">
                        {session.user_identifier || "—"}
                      </TableCell>
                      <TableCell className="text-text-muted">{formatDateTime(session.started_at)}</TableCell>
                      <TableCell className="text-text-muted">{formatDateTime(session.last_seen_at)}</TableCell>
                      <TableCell className="text-right font-mono text-text">{session.request_count}</TableCell>
                      <TableCell>
                        <span className={cn("font-mono font-medium", getRiskColor(session.risk_score))}>
                          {(session.risk_score * 100).toFixed(1)}%
                        </span>
                      </TableCell>
                      <TableCell>
                        <span className={cn("font-mono", getRiskColor(session.anomaly_score))}>
                          {(session.anomaly_score * 100).toFixed(1)}%
                        </span>
                      </TableCell>
                      <TableCell className="text-right font-mono text-text">{session.endpoint_count}</TableCell>
                      <TableCell>
                        <Badge variant="neutral">{session.current_state || "active"}</Badge>
                      </TableCell>
                      <TableCell>
                        <Button variant="ghost" size="icon" onClick={(e) => { e.stopPropagation(); handleViewSession(session); }}>
                          <ArrowUpDown className="w-4 h-4" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))
                ) : (
                  <TableRow>
                    <TableCell colSpan={11} className="py-8 text-center text-text-muted">
                      No sessions found. Generate traffic to create sessions.
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      {selectedSession && (
        <SessionDetailModal session={selectedSession} onClose={() => setSelectedSession(null)} />
      )}
    </div>
  );
}

function SessionDetailModal({ session, onClose }: { session: Session; onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center" onClick={onClose}>
      <div className="fixed inset-0 bg-black/30" />
      <div className="bg-surface w-full max-w-4xl h-[80vh] flex flex-col shadow-xl relative" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between p-4 border-b border-border">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-primary-light">
              <GitBranch className="w-5 h-5 text-primary" />
            </div>
            <div>
              <h2 className="font-semibold text-text">Session Details</h2>
              <p className="text-sm text-text-muted">{session.session_key}</p>
            </div>
          </div>
          <Button variant="ghost" size="icon" onClick={onClose}>
            <X className="w-5 h-5" />
          </Button>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <Card><CardContent className="p-4"><div className="text-text-secondary text-sm">Source IP</div><div className="font-mono text-text mt-1">{session.source_ip}</div></CardContent></Card>
            <Card><CardContent className="p-4"><div className="text-text-secondary text-sm">Requests</div><div className="text-2xl font-semibold text-text mt-1">{session.request_count}</div></CardContent></Card>
            <Card><CardContent className="p-4"><div className="text-text-secondary text-sm">Risk Score</div><div className={cn("text-2xl font-semibold mt-1", getRiskColor(session.risk_score ?? 0))}>{session.risk_score != null ? (session.risk_score * 100).toFixed(1) + "%" : "—"}</div></CardContent></Card>
            <Card><CardContent className="p-4"><div className="text-text-secondary text-sm">Anomaly</div><div className={cn("text-2xl font-semibold mt-1", getRiskColor(session.anomaly_score ?? 0))}>{session.anomaly_score != null ? (session.anomaly_score * 100).toFixed(1) + "%" : "—"}</div></CardContent></Card>
          </div>

          <Card>
            <CardHeader>
              <h3 className="font-medium text-text">Request Timeline</h3>
            </CardHeader>
            <CardContent>
              <div className="space-y-2 max-h-96 overflow-y-auto">
                {session.endpoint_sequence && session.endpoint_sequence.length > 0 ? (
                  session.endpoint_sequence.map((ep: any, i: number) => {
                    const endpointName = typeof ep === "string" ? ep : ep?.endpoint || "Unknown";
                    const timestamp = typeof ep === "object" && ep?.timestamp ? new Date(ep.timestamp).toLocaleTimeString() : null;
                    const risk = typeof ep === "object" ? ep?.risk : null;
                    const decision = typeof ep === "object" ? ep?.decision : null;

                    return (
                      <div key={i} className="flex items-center gap-3 p-3 rounded-lg bg-surface-hover border border-border/50">
                        <div className="w-8 h-8 rounded-full bg-primary-light flex items-center justify-center text-primary text-sm font-medium">
                          {i + 1}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="font-mono text-sm text-text truncate">{endpointName}</div>
                          {timestamp && <div className="text-xs text-text-muted">{timestamp}</div>}
                        </div>
                        {risk != null && (
                          <div className={cn("font-mono text-sm", getRiskColor(risk))}>
                            {(risk * 100).toFixed(0)}%
                          </div>
                        )}
                        {decision && (
                          <Badge variant={decision === "block" ? "danger" : decision === "monitor" ? "info" : "success"} className="text-xs">
                            {decision}
                          </Badge>
                        )}
                      </div>
                    );
                  })
                ) : (
                  <div className="text-center text-text-muted py-8">No request timeline available</div>
                )}
              </div>
            </CardContent>
          </Card>

          {session.risk_timeline && session.risk_timeline.length > 0 && (
            <Card>
              <CardHeader>
                <h3 className="font-medium text-text">Risk Timeline</h3>
              </CardHeader>
              <CardContent>
                <div className="h-48 flex items-end gap-1 px-2">
                  {session.risk_timeline.slice(-30).map((point, i) => (
                    <div
                      key={i}
                      className="flex-1 rounded-t transition-all duration-200"
                      style={{
                        height: `${Math.max(point.risk_score * 100, 2)}%`,
                        backgroundColor: getRiskColor(point.risk_score).replace("text-", "bg-").replace("bg-", "bg-") + "20",
                        borderColor: getRiskColor(point.risk_score).replace("text-", ""),
                        borderWidth: "1px",
                        borderStyle: "solid",
                        borderBottom: "none",
                      }}
                      title={`${point.risk_score * 100}% at ${new Date(point.timestamp).toLocaleTimeString()}`}
                    />
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}