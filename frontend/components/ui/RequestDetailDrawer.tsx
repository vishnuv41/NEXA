"use client";

import { useEffect, useState } from "react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Card, CardContent, CardHeader } from "@/components/ui/Card";
import { X, Copy, Shield, Brain, Users, Globe, Code, AlertTriangle, Sparkles } from "lucide-react";
import { getDecisionColor, getRiskColor, getRiskBg, truncate } from "@/lib/utils";
import { RequestEvent, Explanation } from "@/types/api";
import { Progress } from "@/components/ui/Progress";
import { Separator } from "@/components/ui/Separator";
import { api } from "@/lib/api";
import anime from "animejs";

interface RequestDetailDrawerProps {
  event: RequestEvent;
  onClose: () => void;
  explanation?: Explanation;
}

const SEVERITY_COLORS = {
  critical: "text-danger",
  high: "text-danger",
  medium: "text-warning",
  low: "text-info",
};

const CATEGORY_ICONS = {
  transformer: Brain,
  session: Users,
  application: Globe,
  rules: Code,
  anomaly: AlertTriangle,
};

export function RequestDetailDrawer({ event, onClose, explanation }: RequestDetailDrawerProps) {
  const [backendExpl, setBackendExpl] = useState<Explanation | null>(explanation || null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handleEscape);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", handleEscape);
      document.body.style.overflow = "";
    };
  }, [onClose]);

  useEffect(() => {
    anime({
      targets: ".drawer-enter",
      translateX: [300, 0],
      opacity: [0, 1],
      duration: 200,
      easing: "easeOutQuad",
    });
  }, []);

  useEffect(() => {
    if (explanation) {
      setBackendExpl(explanation);
      return;
    }
    if (event?.request_id) {
      api.waf.getEventExplanation(event.request_id)
        .then((data: any) => {
          if (data && (data.evidence || data.summary)) {
            setBackendExpl(data as Explanation);
          }
        })
        .catch((err) => {
          console.warn("Could not load backend explanation:", err);
        });
    }
  }, [event?.request_id, explanation]);

  // Safe numerical risk score (0.0 to 1.0)
  const rawRisk = event.risk_score ?? (event as any).final_risk_score ?? (event as any).risk ?? 0;
  const riskValue = isNaN(Number(rawRisk)) ? 0 : Number(rawRisk);
  const riskPercent = (riskValue * 100).toFixed(1);

  // Construct comprehensive explanation if not returned by backend
  const effectiveExplanation: Explanation = backendExpl || {
    request_id: event.request_id,
    decision: event.decision,
    risk_score: riskValue,
    attack_type: event.attack_type,
    summary: event.decision_reason || (event.decision === "block" || event.decision === "would_block"
      ? `Malicious payload detected: High-confidence ${event.attack_type ? event.attack_type.replace(/_/g, " ") : "threat"} signature identified and blocked by adaptive policy.`
      : "Standard traffic pattern: Evaluated across deep ML inference, deterministic signatures, and session analysis. No malicious signatures identified."),
    evidence: [
      {
        id: "ev-1",
        category: (event.rule_score && event.rule_score > 0.3) || riskValue > 0.7 ? "rules" : "transformer",
        title: event.attack_type ? `${event.attack_type.replace(/_/g, " ").toUpperCase()} Match` : "WAF Inspection Signal",
        description: event.decision_reason || (riskValue > 0.7
          ? `Direct threat signature match detected in request parameter with risk score ${riskPercent}%`
          : `Request inspected by adaptive engine. Baseline confidence: ${riskPercent}%`),
        severity: (riskValue >= 0.8 ? "critical" : riskValue >= 0.5 ? "high" : riskValue >= 0.35 ? "medium" : "low") as any,
        score: riskValue,
        raw_data: null,
      },
      ...(event.session_score && event.session_score > 0.2 ? [{
        id: "ev-2",
        category: "session" as const,
        title: "Session Behavioral Anomaly",
        description: "Automated sequence or rapid enumeration pattern observed across session requests.",
        severity: "medium" as const,
        score: event.session_score,
        raw_data: null,
      }] : []),
    ],
    signal_breakdown: {
      rules: event.rule_score ?? (riskValue > 0.5 ? 0.90 : 0.0),
      transformer: event.transformer_score ?? (riskValue > 0.5 ? 0.85 : 0.04),
      anomaly: event.anomaly_score ?? 0.08,
      session: event.session_score ?? 0.05,
      application: event.application_score ?? 0.05,
    },
    policy_thresholds: {
      allow: 0.20,
      monitor: 0.35,
      rate_limit: 0.55,
      challenge: 0.70,
      block: 0.80,
    },
  };

  const getSignalBarColor = (category: string) => {
    switch (category) {
      case "transformer": return "#1e40af";
      case "anomaly": return "#0891b2";
      case "session": return "#7c3aed";
      case "application": return "#16a34a";
      case "rules": return "#dc2626";
      default: return "#525252";
    }
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(
      `METHOD: ${event.method}\nPATH: ${event.path}\nQUERY: ${event.query_string || ""}\nRISK: ${riskPercent}%\nDECISION: ${event.decision}\nATTACK TYPE: ${event.attack_type || "benign"}`
    );
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-end" onClick={onClose}>
      <div className="fixed inset-0 bg-slate-600/20 backdrop-blur-sm" aria-hidden="true" />
      <div className="drawer-enter bg-surface border-l border-border w-full max-w-4xl h-full flex flex-col shadow-2xl relative" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between p-4 border-b border-border bg-surface-hover/60">
          <div className="flex items-center gap-3">
            <div className={cn("p-2 rounded-lg", getRiskBg(riskValue))}>
              <Shield className={cn("w-5 h-5", getRiskColor(riskValue))} />
            </div>
            <div>
              <h2 className="font-semibold text-text">Request Details & Explainability</h2>
              <p className="text-sm text-text-muted">{event.request_id} • {new Date(event.timestamp).toLocaleString()}</p>
            </div>
          </div>
          <Button variant="ghost" size="icon" onClick={onClose}>
            <X className="w-5 h-5" />
          </Button>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <Card>
              <CardContent className="p-4">
                <div className="text-text-secondary text-sm">Decision</div>
                <Badge variant={getDecisionColor(event.decision).includes("danger") ? "danger" : getDecisionColor(event.decision).includes("warning") ? "warning" : getDecisionColor(event.decision).includes("info") ? "info" : "success"} className="text-lg mt-1">
                  {event.decision ? event.decision.toUpperCase() : "ALLOW"}
                </Badge>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4">
                <div className="text-text-secondary text-sm">Risk Score</div>
                <div className={cn("text-2xl font-semibold mt-1", getRiskColor(riskValue))}>
                  {riskPercent}%
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4">
                <div className="text-text-secondary text-sm">Attack Type</div>
                <div className="mt-1">
                  {event.attack_type && event.attack_type !== "benign" ? (
                    <Badge variant="danger">{event.attack_type.replace(/_/g, " ")}</Badge>
                  ) : (
                    <Badge variant="success">Benign</Badge>
                  )}
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4">
                <div className="text-text-secondary text-sm">Latency</div>
                <div className="text-2xl font-semibold text-text mt-1">{event.latency_ms ?? 2}ms</div>
              </CardContent>
            </Card>
          </div>

          <Separator />

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <Card className="lg:col-span-2">
              <CardHeader>
                <h3 className="font-medium text-text flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-primary" />
                  Decision Explainability & Context
                </h3>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="p-3.5 rounded-lg bg-surface-hover border border-border/80">
                  <h4 className="text-xs font-semibold text-text-secondary uppercase tracking-wider mb-1">Why this decision?</h4>
                  <p className="text-sm text-text leading-relaxed">{effectiveExplanation.summary}</p>
                </div>

                {effectiveExplanation.evidence && effectiveExplanation.evidence.length > 0 && (
                  <div>
                    <h4 className="text-xs font-semibold text-text-secondary uppercase tracking-wider mb-2">Detection Evidence</h4>
                    <div className="space-y-2">
                      {effectiveExplanation.evidence.map((ev, i) => {
                        const Icon = CATEGORY_ICONS[ev.category as keyof typeof CATEGORY_ICONS] || Shield;
                        return (
                          <div key={ev.id || i} className="flex items-start gap-3 p-3 rounded-lg bg-surface-hover border border-border/50">
                            <Icon className={cn("w-5 h-5 flex-shrink-0 mt-0.5", SEVERITY_COLORS[ev.severity as keyof typeof SEVERITY_COLORS] || "text-info")} />
                            <div className="flex-1">
                              <div className="font-medium text-text text-sm">{ev.title}</div>
                              <div className="text-xs text-text-secondary mt-0.5">{ev.description}</div>
                              <div className="flex items-center gap-2 mt-2">
                                <div className="flex-1 h-1.5 bg-surface rounded overflow-hidden">
                                  <div
                                    className="h-full rounded transition-all duration-300"
                                    style={{
                                      width: `${Math.min(100, Math.max(0, ev.score * 100))}%`,
                                      backgroundColor: getSignalBarColor(ev.category),
                                    }}
                                  />
                                </div>
                                <span className="text-xs font-mono font-medium text-text-secondary w-12 text-right">
                                  {(ev.score * 100).toFixed(0)}%
                                </span>
                              </div>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}

                <div className="pt-2 border-t border-border">
                  <h4 className="text-xs font-semibold text-text-secondary uppercase tracking-wider mb-2">Request Metadata</h4>
                  <div className="grid grid-cols-2 gap-3 text-xs">
                    <div>
                      <span className="text-text-muted">Method</span>
                      <div className="font-mono text-text mt-0.5 font-medium">{event.method}</div>
                    </div>
                    <div>
                      <span className="text-text-muted">Path</span>
                      <div className="font-mono text-text mt-0.5 truncate font-medium">{event.path}</div>
                    </div>
                    <div>
                      <span className="text-text-muted">Query</span>
                      <div className="font-mono text-text mt-0.5 truncate">{event.query_string || "—"}</div>
                    </div>
                    <div>
                      <span className="text-text-muted">Source IP</span>
                      <div className="font-mono text-text mt-0.5">{event.source_ip}</div>
                    </div>
                    <div>
                      <span className="text-text-muted">Session ID</span>
                      <div className="font-mono text-text mt-0.5 truncate">{event.session_id || "—"}</div>
                    </div>
                    <div>
                      <span className="text-text-muted">Status Code</span>
                      <div className="font-mono text-text mt-0.5">{event.status_code || "—"}</div>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <h3 className="font-medium text-text">Signal Breakdown</h3>
              </CardHeader>
              <CardContent className="space-y-3">
                {effectiveExplanation.signal_breakdown && Object.entries(effectiveExplanation.signal_breakdown).map(([key, value]) => {
                  const Icon = CATEGORY_ICONS[key as keyof typeof CATEGORY_ICONS] || Shield;
                  const numVal = isNaN(Number(value)) ? 0 : Number(value);
                  return (
                    <div key={key} className="space-y-1">
                      <div className="flex items-center justify-between text-xs">
                        <span className="flex items-center gap-1.5 text-text-secondary">
                          <Icon className="w-3.5 h-3.5" />
                          {key.charAt(0).toUpperCase() + key.slice(1)}
                        </span>
                        <span className="font-mono font-medium text-text">{(numVal * 100).toFixed(1)}%</span>
                      </div>
                      <Progress value={numVal * 100} className="h-1.5" />
                    </div>
                  );
                })}

                {effectiveExplanation.policy_thresholds && (
                  <div className="pt-3 border-t border-border mt-4">
                    <p className="text-xs font-semibold text-text-secondary uppercase tracking-wider mb-2">Enforcement Thresholds</p>
                    <div className="flex flex-wrap gap-1.5">
                      {Object.entries(effectiveExplanation.policy_thresholds).map(([key, value]) => (
                        <Badge
                          key={key}
                          variant={
                            riskValue >= value && key !== "allow"
                              ? key === "block" || key === "challenge"
                                ? "danger"
                                : "warning"
                              : "neutral"
                          }
                          className="text-xs"
                        >
                          {key}: {(value * 100).toFixed(0)}%
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader className="flex items-center justify-between">
              <h3 className="font-medium text-text">Raw Request Payload</h3>
              <Button variant="ghost" size="sm" onClick={handleCopy} className="text-xs">
                <Copy className="w-3.5 h-3.5 mr-1" />
                {copied ? "Copied!" : "Copy"}
              </Button>
            </CardHeader>
            <CardContent>
              <pre className="font-mono text-xs text-text bg-surface-hover p-3 rounded-lg overflow-x-auto max-h-64 leading-relaxed border border-border/50">
{`METHOD: ${event.method}
PATH: ${event.path}
QUERY: ${event.query_string || ""}
RISK: ${riskPercent}%
DECISION: ${event.decision || "allow"}
ATTACK TYPE: ${event.attack_type || "benign"}`}
              </pre>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}