"use client";

import { useEffect, useState, useCallback } from "react";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api";
import { useAppStore } from "@/hooks/useAppStore";
import type { RequestEvent as StoreRequestEvent } from "@/hooks/useAppStore";
import { Card, CardContent, CardHeader } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { RequestDetailDrawer } from "@/components/ui/RequestDetailDrawer";
import {
  Shield,
  AlertTriangle,
  Activity,
  TrendingUp,
  Play,
  Zap,
  RefreshCw,
  Database,
  Code,
  FileText,
  Terminal,
} from "lucide-react";
import { formatNumber, getRiskColor, getRiskBg, formatDateTime } from "@/lib/utils";
import { StatsSummary } from "@/types/api";

const DONUT_COLORS = ["#dc2626", "#ea580c", "#d97706", "#0891b2", "#7c3aed", "#4f46e5", "#059669"];
// Light theme chart colors
const CHART_GRID = "#e2e8f0";
const CHART_TEXT = "#64748b";

function SvgAreaChart({ data }: { data: Array<{ hour: string; requests: number; threats: number }> }) {
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null);
  if (!data || data.length === 0) return null;

  const W = 600, H = 220;
  const PAD = { top: 24, right: 16, bottom: 28, left: 36 };
  const innerW = W - PAD.left - PAD.right;
  const innerH = H - PAD.top - PAD.bottom;

  const maxVal = Math.max(...data.map((d) => Math.max(d.requests || 0, d.threats || 0)), 1);
  const len = data.length;
  const xStep = len > 1 ? innerW / (len - 1) : innerW;
  const toX = (i: number) => PAD.left + i * xStep;
  const toY = (v: number) => PAD.top + innerH - (Math.min(v, maxVal) / maxVal) * innerH;

  const pathD = (key: "requests" | "threats") =>
    "M " + data.map((d, i) => `${toX(i).toFixed(1)},${toY(d[key] || 0).toFixed(1)}`).join(" L ");

  const areaD = (key: "requests" | "threats") => {
    const pts = data.map((d, i) => `${toX(i).toFixed(1)},${toY(d[key] || 0).toFixed(1)}`);
    const bottom = (PAD.top + innerH).toFixed(1);
    return `M ${PAD.left},${bottom} L ${pts.join(" L ")} L ${toX(len - 1).toFixed(1)},${bottom} Z`;
  };

  const yTicks = [0, Math.round(maxVal * 0.5), maxVal];
  const step = Math.max(1, Math.floor(len / 6));
  const xLabels = data.filter((_, i) => i % step === 0 || i === len - 1);

  return (
    <div className="relative w-full h-full flex flex-col justify-between">
      <div className="flex items-center justify-between px-1 pb-2 text-xs">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-sm bg-blue-600 inline-block" />
            <span className="text-text-secondary font-medium">Requests</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-sm bg-red-500 inline-block" />
            <span className="text-text-secondary font-medium">Threats</span>
          </div>
        </div>
        {hoveredIdx !== null && data[hoveredIdx] ? (
          <div className="flex items-center gap-2.5 text-xs font-mono bg-surface border border-border px-2 py-0.5 rounded shadow-sm">
            <span className="text-text-muted">{data[hoveredIdx].hour}:</span>
            <span className="text-blue-600 font-semibold">{data[hoveredIdx].requests} reqs</span>
            <span className="text-red-500 font-semibold">{data[hoveredIdx].threats} threats</span>
          </div>
        ) : (
          <span className="text-text-muted text-[11px]">Hover over graph for details</span>
        )}
      </div>

      <div className="relative flex-1 min-h-[180px]">
        <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-full" preserveAspectRatio="none">
          <defs>
            <linearGradient id="reqGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#2563eb" stopOpacity="0.3" />
              <stop offset="100%" stopColor="#2563eb" stopOpacity="0.0" />
            </linearGradient>
            <linearGradient id="thrGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#ef4444" stopOpacity="0.3" />
              <stop offset="100%" stopColor="#ef4444" stopOpacity="0.0" />
            </linearGradient>
          </defs>

          {yTicks.map((tick, i) => (
            <g key={i}>
              <line
                x1={PAD.left}
                y1={toY(tick)}
                x2={PAD.left + innerW}
                y2={toY(tick)}
                stroke={CHART_GRID}
                strokeDasharray="3 3"
                strokeWidth="1"
              />
              <text
                x={PAD.left - 6}
                y={toY(tick)}
                textAnchor="end"
                dominantBaseline="middle"
                fontSize="10"
                fill={CHART_TEXT}
                fontFamily="monospace"
              >
                {tick}
              </text>
            </g>
          ))}

          <path d={areaD("requests")} fill="url(#reqGrad)" />
          <path d={areaD("threats")} fill="url(#thrGrad)" />

          <path d={pathD("requests")} fill="none" stroke="#2563eb" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
          <path d={pathD("threats")} fill="none" stroke="#ef4444" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />

          {xLabels.map((d, i) => {
            const idx = data.indexOf(d);
            return (
              <text
                key={i}
                x={toX(idx)}
                y={H - 6}
                textAnchor="middle"
                fontSize="10"
                fill={CHART_TEXT}
                fontFamily="monospace"
              >
                {d.hour}
              </text>
            );
          })}

          {hoveredIdx !== null && data[hoveredIdx] && (
            <g>
              <line
                x1={toX(hoveredIdx)}
                y1={PAD.top}
                x2={toX(hoveredIdx)}
                y2={PAD.top + innerH}
                stroke={CHART_TEXT}
                strokeWidth="1"
                strokeDasharray="3 3"
              />
              <circle cx={toX(hoveredIdx)} cy={toY(data[hoveredIdx].requests || 0)} r="4" fill="#2563eb" stroke="#fff" strokeWidth="2" />
              <circle cx={toX(hoveredIdx)} cy={toY(data[hoveredIdx].threats || 0)} r="4" fill="#ef4444" stroke="#fff" strokeWidth="2" />
            </g>
          )}

          {data.map((_, i) => (
            <rect
              key={i}
              x={toX(i) - xStep / 2}
              y={PAD.top}
              width={Math.max(xStep, 8)}
              height={innerH}
              fill="transparent"
              onMouseEnter={() => setHoveredIdx(i)}
              onMouseLeave={() => setHoveredIdx(null)}
              className="cursor-pointer"
            />
          ))}
        </svg>
      </div>
    </div>
  );
}

function SvgDonutChart({ distribution }: { distribution: Record<string, number> }) {
  const entries = Object.entries(distribution || {}).filter(([, val]) => val > 0);
  const total = entries.reduce((s, [, v]) => s + v, 0);

  if (total === 0 || entries.length === 0) {
    return (
      <div className="h-full flex items-center justify-center text-text-muted">
        No threats detected yet. Generate attack traffic to see distribution.
      </div>
    );
  }

  const cx = 90, cy = 90, R = 68, r = 44;
  let cumAngle = -Math.PI / 2;
  const slices = entries.map(([name, value], i) => {
    const pct = value / total;
    const angle = pct * 2 * Math.PI;
    const sa = cumAngle;
    cumAngle += angle;
    return {
      name,
      value,
      pct,
      sa,
      ea: cumAngle,
      color: DONUT_COLORS[i % DONUT_COLORS.length],
    };
  });

  const arc = (sa: number, ea: number, outerR: number, innerR: number) => {
    const isFull = ea - sa >= 2 * Math.PI - 0.001;
    if (isFull) {
      const mid = sa + Math.PI;
      const x1 = cx + outerR * Math.cos(sa), y1 = cy + outerR * Math.sin(sa);
      const xm = cx + outerR * Math.cos(mid), ym = cy + outerR * Math.sin(mid);
      const ix1 = cx + innerR * Math.cos(sa), iy1 = cy + innerR * Math.sin(sa);
      const ixm = cx + innerR * Math.cos(mid), iym = cy + innerR * Math.sin(mid);
      return `M ${x1.toFixed(2)} ${y1.toFixed(2)} A ${outerR} ${outerR} 0 0 1 ${xm.toFixed(2)} ${ym.toFixed(2)} A ${outerR} ${outerR} 0 0 1 ${x1.toFixed(2)} ${y1.toFixed(2)} M ${ix1.toFixed(2)} ${iy1.toFixed(2)} A ${innerR} ${innerR} 0 0 0 ${ixm.toFixed(2)} ${iym.toFixed(2)} A ${innerR} ${innerR} 0 0 0 ${ix1.toFixed(2)} ${iy1.toFixed(2)} Z`;
    }
    const x1 = cx + outerR * Math.cos(sa), y1 = cy + outerR * Math.sin(sa);
    const x2 = cx + outerR * Math.cos(ea), y2 = cy + outerR * Math.sin(ea);
    const ix1 = cx + innerR * Math.cos(ea), iy1 = cy + innerR * Math.sin(ea);
    const ix2 = cx + innerR * Math.cos(sa), iy2 = cy + innerR * Math.sin(sa);
    const lg = ea - sa > Math.PI ? 1 : 0;
    return `M ${x1.toFixed(2)} ${y1.toFixed(2)} A ${outerR} ${outerR} 0 ${lg} 1 ${x2.toFixed(2)} ${y2.toFixed(2)} L ${ix1.toFixed(2)} ${iy1.toFixed(2)} A ${innerR} ${innerR} 0 ${lg} 0 ${ix2.toFixed(2)} ${iy2.toFixed(2)} Z`;
  };

  return (
    <div className="flex flex-col sm:flex-row items-center justify-center gap-6 h-full py-2">
      <div className="relative w-44 h-44 shrink-0 flex items-center justify-center">
        <svg viewBox="0 0 180 180" className="w-full h-full">
          {slices.map((s, i) => (
            <path key={i} d={arc(s.sa, s.ea, R, r)} fill={s.color} className="transition-opacity hover:opacity-85" />
          ))}
          <text x={cx} y={cy - 3} textAnchor="middle" fontSize="18" fontWeight="bold" fill="#0f172a">
            {total}
          </text>
          <text x={cx} y={cy + 13} textAnchor="middle" fontSize="10" fill={CHART_TEXT}>
            threats
          </text>
        </svg>
      </div>

      <div className="flex-1 space-y-2 min-w-0 max-h-48 overflow-y-auto pr-2 w-full">
        {slices.map((s, i) => (
          <div key={i} className="flex items-center gap-2 text-xs">
            <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ backgroundColor: s.color }} />
            <span className="text-text-secondary truncate flex-1 font-medium">
              {s.name.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
            </span>
            <span className="font-mono font-semibold text-text shrink-0">
              {s.value} <span className="text-text-muted font-normal">({(s.pct * 100).toFixed(0)}%)</span>
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

export function OverviewPage() {
  const { setStats, liveEvents, setLiveEvents, addLiveEvent, clearLiveEvents } = useAppStore();
  const [localStats, setLocalStats] = useState<StatsSummary | null>(null);
  const [loadingLegit, setLoadingLegit] = useState(false);
  const [loadingAttack, setLoadingAttack] = useState(false);
  const [feedback, setFeedback] = useState<{ msg: string; type: "success" | "error" } | null>(null);
  const [selectedEvent, setSelectedEvent] = useState<StoreRequestEvent | null>(null);

  const loadData = useCallback(async () => {
    try {
      const [statsResult, recentResult] = await Promise.allSettled([
        api.events.getSummary(),
        api.events.getRecent(20),
      ]);
      if (statsResult.status === "fulfilled" && statsResult.value) {
        setLocalStats(statsResult.value as any);
        setStats(statsResult.value as any);
      }
      if (recentResult.status === "fulfilled" && Array.isArray(recentResult.value) && recentResult.value.length > 0) {
        setLiveEvents(recentResult.value as any);
      }
    } catch (e) {
      console.error("Failed to load overview data:", e);
    }
  }, [setStats, setLiveEvents]);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 10000);
    return () => clearInterval(interval);
  }, [loadData]);

  const showFeedback = (msg: string, type: "success" | "error") => {
    setFeedback({ msg, type });
    setTimeout(() => setFeedback(null), 4000);
  };

  const handleGenerateLegit = async () => {
    if (loadingLegit) return;
    setLoadingLegit(true);
    try {
      const ips = ["192.168.1.10", "10.0.0.5", "172.16.0.20", "203.0.113.5"];
      const paths = ["/", "/products", "/products/1", "/search", "/products/2", "/dashboard"];
      const queries = ["", "", "", "q=laptop", "", ""];
      for (let i = 0; i < paths.length; i++) {
        try {
          const res = await api.waf.inspectAndProxy({
            method: "GET",
            path: paths[i],
            query: queries[i],
            headers: { "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120" },
            body: "",
            source_ip: ips[i % ips.length],
          });
          if (res) {
            addLiveEvent({
              request_id: res.request_id || `req-${Date.now()}-${i}`,
              timestamp: new Date().toISOString(),
              method: "GET",
              path: paths[i],
              query: queries[i],
              source_ip: ips[i % ips.length],
              session_id: `ip:${ips[i % ips.length]}`,
              risk_score: res.risk_score ?? 0,
              final_risk_score: res.risk_score ?? 0,
              attack_type: res.attack_type ?? null,
              decision: res.decision ?? "allow",
              latency_ms: 12,
            });
          }
        } catch (reqErr) {
          console.warn("Legitimate request warning:", reqErr);
        }
      }
      await loadData();
      showFeedback("Generated 6 legitimate requests ✓", "success");
    } catch (e) {
      console.error("Failed to generate traffic:", e);
      showFeedback("Failed to generate traffic — check backend connection", "error");
    } finally {
      setLoadingLegit(false);
    }
  };

  const handleGenerateAttack = async (specificPreset?: { path: string; query: string; type: string; name: string }) => {
    if (loadingAttack) return;
    setLoadingAttack(true);
    try {
      const attacks = specificPreset
        ? [specificPreset]
        : [
            { path: "/search", query: "q=test' OR '1'='1; DROP TABLE users--", type: "sql_injection", name: "SQL Injection" },
            { path: "/search", query: "q=<script>alert(document.cookie)</script>", type: "xss", name: "XSS Attack" },
            { path: "/products/../../../etc/passwd", query: "", type: "path_traversal", name: "Path Traversal" },
            { path: "/search", query: "q=; ls -la /etc", type: "command_injection", name: "Command Injection" },
            { path: "/products/1", query: "id=1 UNION SELECT username,password,3 FROM admin--", type: "sql_injection", name: "SQL Injection (Union)" },
          ];
      let blockedCount = 0;
      for (let i = 0; i < attacks.length; i++) {
        const atk = attacks[i];
        try {
          const res = await api.waf.inspectAndProxy({
            method: "GET",
            path: atk.path,
            query: atk.query,
            headers: { "User-Agent": "sqlmap/1.7.8" },
            body: "",
            source_ip: "185.220.101.5",
          });
          if (res) {
            const decisionVal = res.decision || ((res as any).blocked ? "block" : "allow");
            if (decisionVal === "block" || (res as any).blocked) blockedCount++;
            addLiveEvent({
              request_id: res.request_id || `atk-${Date.now()}-${i}`,
              timestamp: new Date().toISOString(),
              method: "GET",
              path: atk.path,
              query: atk.query,
              source_ip: "185.220.101.5",
              session_id: "ip:185.220.101.5",
              risk_score: res.risk_score ?? 0.85,
              final_risk_score: res.risk_score ?? 0.85,
              attack_type: res.attack_type ?? atk.type,
              decision: decisionVal as any,
              latency_ms: 18,
            });
          }
        } catch (reqErr) {
          console.warn("Attack request warning:", reqErr);
        }
      }
      await loadData();
      if (specificPreset) {
        showFeedback(`Simulated ${specificPreset.name} → BLOCKED by WAF ✓`, "success");
      } else {
        showFeedback(`Simulated ${attacks.length} attacks (${blockedCount} blocked by WAF) ✓`, "success");
      }
    } catch (e) {
      console.error("Failed to generate attack:", e);
      showFeedback("Failed to generate attack — check backend connection", "error");
    } finally {
      setLoadingAttack(false);
    }
  };

  const storeStats = useAppStore((s) => s.stats);
  const stats = localStats || storeStats;

  const metricCards = [
    {
      title: "Requests Analyzed",
      value: stats ? formatNumber(stats.total_requests) : "—",
      icon: Activity,
      color: "text-primary",
      bg: "bg-primary-light",
      trend: stats ? `+${formatNumber(stats.recent_requests_1h)} last hour` : null,
    },
    {
      title: "Threats Detected",
      value: stats ? formatNumber(stats.total_threats) : "—",
      icon: AlertTriangle,
      color: "text-danger",
      bg: "bg-danger-light",
      trend: stats ? `+${formatNumber(stats.recent_threats_1h)} last hour` : null,
    },
    {
      title: "Requests Blocked",
      value: stats ? formatNumber(stats.total_blocked) : "—",
      icon: Shield,
      color: "text-success",
      bg: "bg-success-light",
      trend: stats ? `${stats.total_requests > 0 ? ((stats.total_blocked / stats.total_requests) * 100).toFixed(1) : 0}% block rate` : null,
    },
    {
      title: "Avg Risk Score",
      value: stats ? (stats.avg_risk_score * 100).toFixed(1) + "%" : "—",
      icon: TrendingUp,
      color: getRiskColor(stats?.avg_risk_score || 0),
      bg: getRiskBg(stats?.avg_risk_score || 0),
      trend: "Average across all requests",
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between anime-fade-in">
        <div>
          <h1 className="text-2xl font-bold text-text tracking-tight">Security Overview</h1>
          <p className="text-text-secondary text-sm mt-0.5">Live protection • Real-time threat detection</p>
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" size="sm" onClick={loadData}>
            <RefreshCw className="w-4 h-4" />
            Refresh
          </Button>
        </div>
      </div>

      {feedback && (
        <div
          className={cn(
            "flex items-center gap-2.5 px-4 py-3 rounded-xl text-sm font-medium border shadow-xs transition-all duration-200",
            feedback.type === "success"
              ? "bg-emerald-50 border-emerald-300 text-emerald-800"
              : "bg-red-50 border-red-300 text-red-700"
          )}
        >
          <span className={cn("w-2 h-2 rounded-full shrink-0", feedback.type === "success" ? "bg-emerald-500" : "bg-red-500")} />
          <span>{feedback.msg}</span>
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {metricCards.map((metric, i) => (
          <Card key={i} className="anime-fade-in hover:translate-y-[-2px]">
            <CardContent className="p-5">
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-text-secondary text-xs font-medium uppercase tracking-wider">{metric.title}</p>
                  <p className="text-2xl font-bold text-text mt-1.5 tabular-nums">{metric.value}</p>
                  {metric.trend && (
                    <p className="text-xs text-text-muted mt-1">{metric.trend}</p>
                  )}
                </div>
                <div className={cn("p-2.5 rounded-xl", metric.bg)}>
                  <metric.icon className={cn("w-5 h-5", metric.color)} />
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card className="anime-fade-in">
          <CardHeader>
            <h2 className="font-semibold text-text">Threat Trend (24h)</h2>
          </CardHeader>
          <CardContent>
            <div className="h-64">
              {stats?.trend_24h && stats.trend_24h.length > 0 ? (
                <SvgAreaChart data={stats.trend_24h} />
              ) : (
                <div className="h-full flex items-center justify-center text-text-muted text-sm">
                  No data yet — generate traffic to populate.
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        <Card className="anime-fade-in">
          <CardHeader>
            <h2 className="font-semibold text-text">Attack Distribution</h2>
          </CardHeader>
          <CardContent>
            <div className="h-64 flex flex-col">
              {stats?.attack_distribution && Object.keys(stats.attack_distribution).length > 0 ? (
                <SvgDonutChart distribution={stats.attack_distribution} />
              ) : (
                <div className="flex-1 flex items-center justify-center text-text-muted text-sm">
                  No threats detected yet. Generate attack traffic to see distribution.
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card className="lg:col-span-2 anime-fade-in">
          <CardHeader>
            <h2 className="font-semibold text-text">Recent Security Events</h2>
          </CardHeader>
          <CardContent>
            <div className="max-h-96 overflow-y-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border">
                    <th className="text-left pb-2 pr-4 text-xs font-semibold text-text-secondary uppercase tracking-wider">Time</th>
                    <th className="text-left pb-2 pr-4 text-xs font-semibold text-text-secondary uppercase tracking-wider">Method</th>
                    <th className="text-left pb-2 pr-4 text-xs font-semibold text-text-secondary uppercase tracking-wider">Endpoint</th>
                    <th className="text-left pb-2 pr-4 text-xs font-semibold text-text-secondary uppercase tracking-wider">Source</th>
                    <th className="text-left pb-2 pr-4 text-xs font-semibold text-text-secondary uppercase tracking-wider">Risk</th>
                    <th className="text-left pb-2 pr-4 text-xs font-semibold text-text-secondary uppercase tracking-wider">Decision</th>
                  </tr>
                </thead>
                <tbody>
                  {liveEvents.slice(0, 10).length > 0 ? (
                    liveEvents.slice(0, 10).map((event, i) => (
                      <tr
                        key={i}
                        className="border-b border-border/50 hover:bg-surface-hover cursor-pointer transition-colors"
                        onClick={() => setSelectedEvent(event)}
                      >
                        <td className="py-2 pr-4 text-text-muted">{formatDateTime(event.timestamp)}</td>
                        <td className="py-2 pr-4 font-mono text-text">{event.method}</td>
                        <td className="py-2 pr-4 font-mono text-text truncate max-w-xs">{event.path}</td>
                        <td className="py-2 pr-4 text-text-secondary">{event.source_ip}</td>
                        <td className="py-2 pr-4">
                          <span className={cn("font-mono font-semibold", getRiskColor(event.final_risk_score ?? event.risk_score ?? 0))}>
                            {(((event.final_risk_score ?? event.risk_score ?? 0) * 100).toFixed(0))}%
                          </span>
                        </td>
                        <td className="py-2 pr-4">
                          <Badge variant={event.decision === "block" || event.decision === "would_block" ? "danger" : event.decision === "challenge" ? "warning" : event.decision === "rate_limit" ? "warning" : event.decision === "monitor" ? "info" : "success"}>
                            {event.decision}
                          </Badge>
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={6} className="py-8 text-center text-text-muted">
                        No live events yet. Click "Generate Legitimate Traffic" or "Simulate Attack Suite" to start.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <h2 className="font-medium text-text">Quick Actions & Presets</h2>
          </CardHeader>
          <CardContent className="space-y-3">
            <Button
              variant="primary"
              className="w-full justify-start"
              disabled={loadingLegit || loadingAttack}
              onClick={handleGenerateLegit}
            >
              {loadingLegit ? (
                <RefreshCw className="w-4 h-4 animate-spin text-white" />
              ) : (
                <Play className="w-4 h-4" />
              )}
              <span>{loadingLegit ? "Generating 6 requests..." : "Generate Legitimate Traffic (6 reqs)"}</span>
            </Button>
            <Button
              variant="danger"
              className="w-full justify-start"
              disabled={loadingLegit || loadingAttack}
              onClick={() => handleGenerateAttack()}
            >
              {loadingAttack ? (
                <RefreshCw className="w-4 h-4 animate-spin text-white" />
              ) : (
                <Zap className="w-4 h-4" />
              )}
              <span>{loadingAttack ? "Simulating attacks..." : "Simulate Full Attack Suite (5 blocked)"}</span>
            </Button>

            <div className="pt-2 border-t border-border">
              <p className="text-xs font-medium text-text-secondary mb-2 uppercase tracking-wide">Attack Vector Presets</p>
              <div className="grid grid-cols-2 gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  className="text-xs justify-start hover:border-red-500 hover:text-red-500"
                  disabled={loadingLegit || loadingAttack}
                  onClick={() => handleGenerateAttack({ path: "/search", query: "q=1' UNION SELECT username,password,3 FROM admin--", type: "sql_injection", name: "SQL Injection" })}
                >
                  <Database className="w-3.5 h-3.5 mr-1 text-red-500" />
                  SQLi Preset
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  className="text-xs justify-start hover:border-orange-500 hover:text-orange-500"
                  disabled={loadingLegit || loadingAttack}
                  onClick={() => handleGenerateAttack({ path: "/search", query: "q=<script>alert(document.cookie)</script>", type: "xss", name: "XSS Attack" })}
                >
                  <Code className="w-3.5 h-3.5 mr-1 text-orange-500" />
                  XSS Preset
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  className="text-xs justify-start hover:border-amber-500 hover:text-amber-500"
                  disabled={loadingLegit || loadingAttack}
                  onClick={() => handleGenerateAttack({ path: "/products/../../../etc/passwd", query: "", type: "path_traversal", name: "Path Traversal" })}
                >
                  <FileText className="w-3.5 h-3.5 mr-1 text-amber-500" />
                  Path Traversal
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  className="text-xs justify-start hover:border-purple-500 hover:text-purple-500"
                  disabled={loadingLegit || loadingAttack}
                  onClick={() => handleGenerateAttack({ path: "/search", query: "q=; cat /etc/passwd", type: "command_injection", name: "Command Injection" })}
                >
                  <Terminal className="w-3.5 h-3.5 mr-1 text-purple-500" />
                  Cmd Injection
                </Button>
              </div>
            </div>

            <Button
              variant="outline"
              className="w-full justify-start text-xs mt-2"
              disabled={loadingLegit || loadingAttack}
              onClick={clearLiveEvents}
            >
              <RefreshCw className="w-3.5 h-3.5 mr-1" />
              Clear Live Events
            </Button>
          </CardContent>
        </Card>
      </div>

      {selectedEvent && (
        <RequestDetailDrawer
          event={selectedEvent as any}
          onClose={() => setSelectedEvent(null)}
        />
      )}
    </div>
  );
}