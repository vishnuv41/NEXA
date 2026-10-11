"use client";

import { useEffect, useState } from "react";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader } from "@/components/ui/Card";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "@/components/ui/Table";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Progress } from "@/components/ui/Progress";
import {
  FlaskConical,
  Play,
  RefreshCw,
  Download,
  Eye,
  Check,
  X,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  Settings,
  Zap,
} from "lucide-react";
import { getDecisionColor, getRiskColor, truncate } from "@/lib/utils";
import { AttackLabRunResponse, AttackVariantResult, AttackFamily, AttackLabRun } from "@/types/api";
import { Separator } from "@/components/ui/Separator";

const ATTACK_FAMILIES: { id: string; name: string; icon: string }[] = [
  { id: "sql_injection", name: "SQL Injection", icon: "Database" },
  { id: "xss", name: "Cross-Site Scripting (XSS)", icon: "Code" },
  { id: "path_traversal", name: "Path Traversal", icon: "FileText" },
  { id: "command_injection", name: "Command Injection", icon: "Terminal" },
  { id: "mixed", name: "Mixed (All Families)", icon: "FlaskConical" },
];

export function AttackLabPage() {
  const [families, setFamilies] = useState<AttackFamily[]>([]);
  const [selectedFamily, setSelectedFamily] = useState("mixed");
  const [variantCount, setVariantCount] = useState(25);
  const [targetEndpoint, setTargetEndpoint] = useState("/search");
  const [customPayloads, setCustomPayloads] = useState("");
  const [running, setRunning] = useState(false);
  const [runResult, setRunResult] = useState<AttackLabRunResponse | null>(null);
  const [expandedVariants, setExpandedVariants] = useState<Set<string>>(new Set());
  const [runs, setRuns] = useState<AttackLabRun[]>([]);

  useEffect(() => {
    loadFamilies();
    loadRuns();
  }, []);

  const loadFamilies = async () => {
    try {
      const data = await api.attackLab.getFamilies();
      setFamilies(data.families);
    } catch (e) {
      console.error("Failed to load families:", e);
    }
  };

  const loadRuns = async () => {
    try {
      const data = await api.attackLab.listRuns();
      setRuns(data);
    } catch (e) {
      console.error("Failed to load runs:", e);
    }
  };

  const handleRun = async () => {
    setRunning(true);
    setRunResult(null);
    try {
      const basePayloads = customPayloads.trim() ? customPayloads.trim().split("\n").map(p => p.trim()).filter(Boolean) : undefined;
      const result = await api.attackLab.run({
        attack_family: selectedFamily,
        base_payloads: basePayloads,
        variant_count: variantCount,
        target_endpoint: targetEndpoint,
      });
      setRunResult(result);
      loadRuns();
    } catch (e) {
      console.error("Failed to run attack lab:", e);
    }
    setRunning(false);
  };

  const toggleVariant = (variant: string) => {
    setExpandedVariants(prev => {
      const next = new Set(prev);
      if (next.has(variant)) next.delete(variant);
      else next.add(variant);
      return next;
    });
  };

  if (runResult) {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold text-text">Attack Lab Results</h1>
            <p className="text-text-secondary text-sm">Run ID: {runResult.run_id} • {runResult.attack_family}</p>
          </div>
          <Button variant="primary" onClick={() => setRunResult(null)}>
            <RefreshCw className="w-4 h-4" />
            New Test
          </Button>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card><CardContent className="p-4">
            <div className="text-text-secondary text-sm">Variants Tested</div>
            <div className="text-2xl font-semibold text-text">{runResult.total_variants}</div>
          </CardContent></Card>
          <Card><CardContent className="p-4">
            <div className="text-text-secondary text-sm">Detected</div>
            <div className="text-2xl font-semibold text-success">{runResult.detected}</div>
          </CardContent></Card>
          <Card><CardContent className="p-4">
            <div className="text-text-secondary text-sm">Missed</div>
            <div className="text-2xl font-semibold text-danger">{runResult.missed}</div>
          </CardContent></Card>
          <Card><CardContent className="p-4">
            <div className="text-text-secondary text-sm">Detection Rate</div>
            <div className="text-2xl font-semibold text-primary">{runResult.detection_rate != null ? (runResult.detection_rate * 100).toFixed(1) + "%" : "0.0%"}</div>
          </CardContent></Card>
        </div>

        <Card>
          <CardHeader className="flex items-center justify-between">
            <h3 className="font-medium text-text">Variant Results</h3>
            <div className="flex items-center gap-2">
              <Progress value={(runResult.detection_rate ?? 0) * 100} className="w-32 h-2" />
              <span className="text-sm font-mono text-text-secondary">Avg: {runResult.avg_latency_ms != null ? runResult.avg_latency_ms.toFixed(0) : "0"}ms</span>
            </div>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>#</TableHead>
                    <TableHead>Original</TableHead>
                    <TableHead>Variant</TableHead>
                    <TableHead>Transformations</TableHead>
                    <TableHead>Risk</TableHead>
                    <TableHead>Decision</TableHead>
                    <TableHead>Attack Type</TableHead>
                    <TableHead>Latency</TableHead>
                    <TableHead>Status</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {runResult.variants.map((v, i) => (
                    <TableRow key={i}>
                      <TableCell className="font-mono text-text">{i + 1}</TableCell>
                      <TableCell className="font-mono text-xs text-text-secondary truncate max-w-xs" title={v.original}>{truncate(v.original, 30)}</TableCell>
                      <TableCell className="font-mono text-xs truncate max-w-xs" title={v.variant}>{truncate(v.variant, 30)}</TableCell>
                      <TableCell>
                        <div className="flex flex-wrap gap-1">
                          {v.transformations.slice(1).map((t, idx) => (
                            <Badge key={idx} variant="neutral" className="text-xs">{t}</Badge>
                          ))}
                        </div>
                      </TableCell>
                      <TableCell>
                        <span className={cn("font-mono", getRiskColor(v.risk_score ?? 0))}>
                          {v.risk_score != null ? (v.risk_score * 100).toFixed(1) + "%" : "—"}
                        </span>
                      </TableCell>
                      <TableCell>
                        <Badge variant={getDecisionColor(v.decision).includes("danger") ? "danger" : getDecisionColor(v.decision).includes("warning") ? "warning" : getDecisionColor(v.decision).includes("info") ? "info" : "success"}>
                          {v.decision}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        {v.attack_type && v.attack_type !== "benign" ? (
                          <Badge variant="danger" className="text-xs">{v.attack_type.replace("_", " ")}</Badge>
                        ) : (
                          <Badge variant="success" className="text-xs">Benign</Badge>
                        )}
                      </TableCell>
                      <TableCell className="font-mono text-text-secondary">{v.latency_ms}ms</TableCell>
                      <TableCell>
                        {v.detected ? (
                          <span className="flex items-center gap-1 text-success">
                            <Check className="w-3 h-3" />
                            Detected
                          </span>
                        ) : (
                          <span className="flex items-center gap-1 text-danger">
                            <X className="w-3 h-3" />
                            Missed
                          </span>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <h3 className="font-medium text-text">Previous Runs</h3>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Run ID</TableHead>
                    <TableHead>Family</TableHead>
                    <TableHead>Variants</TableHead>
                    <TableHead>Detected</TableHead>
                    <TableHead>Rate</TableHead>
                    <TableHead>Avg Latency</TableHead>
                    <TableHead>Started</TableHead>
                    <TableHead>Status</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {runs.map((run) => (
                    <TableRow key={run.run_id}>
                      <TableCell className="font-mono text-text">{run.run_id}</TableCell>
                      <TableCell>{run.attack_family}</TableCell>
                      <TableCell className="font-mono text-text">{run.total_variants ?? 0}</TableCell>
                      <TableCell className="font-mono text-success">{run.detected ?? 0}</TableCell>
                      <TableCell className="font-mono text-primary">{run.detection_rate != null ? (run.detection_rate * 100).toFixed(1) + "%" : "0.0%"}</TableCell>
                      <TableCell className="font-mono text-text-secondary">{run.avg_latency_ms != null ? run.avg_latency_ms.toFixed(0) + "ms" : "—"}</TableCell>
                      <TableCell className="text-text-secondary">{run.started_at ? new Date(run.started_at).toLocaleString() : "—"}</TableCell>
                      <TableCell>
                        <Badge variant={run.status === "completed" ? "success" : "info"}>{run.status}</Badge>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-text">Attack Lab</h1>
          <p className="text-text-secondary text-sm">Generate adversarial variants and test WAF robustness</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card className="lg:col-span-2">
          <CardHeader>
            <h3 className="font-medium text-text flex items-center gap-2">
              <FlaskConical className="w-5 h-5" />
              Test Configuration
            </h3>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-text mb-2">Attack Family</label>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                {families.map((fam) => (
                  <button
                    key={fam.id}
                    onClick={() => setSelectedFamily(fam.id)}
                    className={cn(
                      "p-3 rounded-lg border transition-all text-left",
                      selectedFamily === fam.id
                        ? "border-primary bg-primary-light"
                        : "border-border hover:border-primary/50"
                    )}
                  >
                    <div className="font-medium text-text">{fam.name}</div>
                    <div className="text-xs text-text-muted">{fam.description}</div>
                  </button>
                ))}
              </div>
            </div>

            <Separator />

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-text mb-2">Variant Count</label>
                <Input
                  type="number"
                  min="1"
                  max="100"
                  value={variantCount}
                  onChange={(e) => setVariantCount(Number(e.target.value))}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-text mb-2">Target Endpoint</label>
                <Input
                  value={targetEndpoint}
                  onChange={(e) => setTargetEndpoint(e.target.value)}
                  placeholder="/search"
                />
              </div>
            </div>

            <Separator />

            <div>
              <label className="block text-sm font-medium text-text mb-2">Custom Base Payloads (optional, one per line)</label>
              <textarea
                value={customPayloads}
                onChange={(e) => setCustomPayloads(e.target.value)}
                rows={6}
                className="input font-mono text-sm"
                placeholder="SELECT * FROM users&#10;' OR 1=1--&#10;<script>alert(1)</script>"
              />
            </div>

            <Button variant="primary" size="lg" className="w-full" onClick={handleRun} disabled={running}>
              {running ? (
                <>
                  <FlaskConical className="w-4 h-4 animate-spin" />
                  Running Test...
                </>
              ) : (
                <>
                  <Play className="w-4 h-4" />
                  Run Robustness Test
                </>
              )}
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <h3 className="font-medium text-text flex items-center gap-2">
              <Zap className="w-5 h-5" />
              Quick Start
            </h3>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="p-3 rounded-lg bg-surface-hover border border-border">
              <p className="font-medium text-text">Default Payloads</p>
              <p className="text-sm text-text-secondary mt-1">Each family includes 10 base payloads that are automatically transformed into {variantCount} variants using encoding, obfuscation, and evasion techniques.</p>
            </div>

            <div className="space-y-2">
              {families.map((fam) => (
                <div key={fam.id} className="p-3 rounded-lg border border-border hover:bg-surface-hover transition-colors">
                  <div className="font-medium text-text">{fam.name}</div>
                  <div className="text-xs text-text-muted mt-1">
                    {fam.default_payloads?.slice(0, 3).map((p: string) => truncate(p, 40)).join(" • ")}
                    {fam.default_payloads && fam.default_payloads.length > 3 && "..."}
                  </div>
                </div>
              ))}
            </div>

            <Separator />

            <h4 className="font-medium text-text">Transformations Applied</h4>
            <div className="flex flex-wrap gap-1">
              {[
                "URL Encode", "Double Encode", "Random Case", "Add Whitespace",
                "SQL Comment", "Base64", "Hex Encode", "Unicode", "HTML Entity",
                "Null Byte", "Param Pollution", "JSON Wrap", "XML Wrap"
              ].map((t) => (
                <Badge key={t} variant="neutral" className="text-xs">{t}</Badge>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}