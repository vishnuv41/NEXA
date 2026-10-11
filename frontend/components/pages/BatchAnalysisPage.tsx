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
  Database,
  Upload,
  Download,
  RefreshCw,
  Eye,
  Play,
  Check,
  X,
  Clock,
  AlertTriangle,
  FileText,
  BarChart2,
} from "lucide-react";
import { formatNumber, getDecisionColor, getRiskColor, truncate } from "@/lib/utils";
import { BatchRunResponse, BatchResultItem, BatchRun } from "@/types/api";

export function BatchAnalysisPage() {
  const [runs, setRuns] = useState<BatchRun[]>([]);
  const [selectedRun, setSelectedRun] = useState<BatchRunResponse | null>(null);
  const [uploading, setUploading] = useState(false);
  const [hasLabels, setHasLabels] = useState(false);
  const [dragActive, setDragActive] = useState(false);

  useEffect(() => {
    loadRuns();
  }, []);

  const loadRuns = async () => {
    try {
      const data = await api.batch.listRuns();
      setRuns(data);
    } catch (e) {
      console.error("Failed to load runs:", e);
    }
  };

  const handleUpload = async (file: File) => {
    setUploading(true);
    try {
      await api.batch.analyze(file, hasLabels);
      loadRuns();
    } catch (e) {
      console.error("Failed to upload batch:", e);
    }
    setUploading(false);
  };

  const handleLoadSample = async () => {
    setUploading(true);
    try {
      const resp = await fetch("/sample_waf_dataset.csv");
      const text = await resp.text();
      const file = new File([text], "sample_waf_dataset.csv", { type: "text/csv" });
      await api.batch.analyze(file, true);
      await loadRuns();
    } catch (e) {
      console.error("Failed to load sample dataset:", e);
    }
    setUploading(false);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setDragActive(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setDragActive(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragActive(false);
    const file = e.dataTransfer.files[0];
    if (file && (file.name.endsWith(".csv") || file.name.endsWith(".json"))) {
      handleUpload(file);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleUpload(file);
  };

  const handleViewRun = async (runId: string) => {
    try {
      const data = await api.batch.getRun(runId);
      setSelectedRun(data);
    } catch (e) {
      console.error("Failed to load run:", e);
    }
  };

  const handleExport = async (runId: string, format: "json" | "csv") => {
    try {
      const data = await api.batch.exportResults(runId, format);
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `batch-${runId}.${format}`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      console.error("Failed to export:", e);
    }
  };

  if (selectedRun) {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold text-text">Batch Analysis Results</h1>
            <p className="text-text-secondary text-sm">Run: {selectedRun.run_name} • {selectedRun.dataset_name}</p>
          </div>
          <Button variant="primary" onClick={() => setSelectedRun(null)}>
            <RefreshCw className="w-4 h-4" />
            Back to Runs
          </Button>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
          <Card><CardContent className="p-4">
            <div className="flex items-center gap-2"><Database className="w-5 h-5 text-primary" /><span className="text-text-secondary text-sm">Total Samples</span></div>
            <div className="text-2xl font-semibold text-text mt-1">{formatNumber(selectedRun.total_samples)}</div>
          </CardContent></Card>
          <Card><CardContent className="p-4">
            <div className="flex items-center gap-2"><Check className="w-5 h-5 text-success" /><span className="text-text-secondary text-sm">Allowed</span></div>
            <div className="text-2xl font-semibold text-success mt-1">
              {selectedRun.results?.filter((r: BatchResultItem) => r.decision !== "block" && r.decision !== "would_block").length || 0}
            </div>
          </CardContent></Card>
          <Card><CardContent className="p-4">
            <div className="flex items-center gap-2"><X className="w-5 h-5 text-danger" /><span className="text-text-secondary text-sm">Blocked</span></div>
            <div className="text-2xl font-semibold text-danger mt-1">
              {selectedRun.results?.filter((r: BatchResultItem) => r.decision === "block" || r.decision === "would_block").length || 0}
            </div>
          </CardContent></Card>
          <Card><CardContent className="p-4">
            <div className="flex items-center gap-2"><AlertTriangle className="w-5 h-5 text-warning" /><span className="text-text-secondary text-sm">Threats</span></div>
            <div className="text-2xl font-semibold text-warning mt-1">
              {selectedRun.results?.filter((r: BatchResultItem) => r.attack_type && r.attack_type !== "benign").length || 0}
            </div>
          </CardContent></Card>
          <Card><CardContent className="p-4">
            <div className="flex items-center gap-2"><BarChart2 className="w-5 h-5 text-info" /><span className="text-text-secondary text-sm">F1 Score</span></div>
            <div className="text-2xl font-semibold text-primary mt-1">
              {(selectedRun as any).f1 ? ((selectedRun as any).f1 * 100).toFixed(1) + "%" : "N/A"}
            </div>
          </CardContent></Card>
        </div>

        {selectedRun.results && selectedRun.results.length > 0 && (
          <Card>
            <CardHeader className="flex items-center justify-between">
              <h3 className="font-medium text-text">Sample Results</h3>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={() => handleExport(selectedRun.run_name, "csv")}>
                  <Download className="w-4 h-4" />
                  CSV
                </Button>
                <Button variant="outline" size="sm" onClick={() => handleExport(selectedRun.run_name, "json")}>
                  <Download className="w-4 h-4" />
                  JSON
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>#</TableHead>
                      <TableHead>Method</TableHead>
                      <TableHead>Path</TableHead>
                      <TableHead>Risk</TableHead>
                      <TableHead>Attack Type</TableHead>
                      <TableHead>Decision</TableHead>
                      <TableHead>Latency</TableHead>
                      {selectedRun.results![0].ground_truth && <TableHead>Ground Truth</TableHead>}
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {selectedRun.results!.slice(0, 100).map((r, i) => (
                      <TableRow key={i}>
                        <TableCell className="font-mono text-text">{i + 1}</TableCell>
                        <TableCell><span className="font-mono text-text bg-surface-hover px-1.5 py-0.5 rounded">{r.method}</span></TableCell>
                        <TableCell className="font-mono text-text truncate max-w-md">{r.path}</TableCell>
                        <TableCell><span className={cn("font-mono", getRiskColor(r.risk_score ?? 0))}>{r.risk_score != null ? (r.risk_score * 100).toFixed(1) + "%" : "—"}</span></TableCell>
                        <TableCell>
                          {r.attack_type && r.attack_type !== "benign" ? (
                            <Badge variant="danger" className="text-xs">{r.attack_type.replace("_", " ")}</Badge>
                          ) : (
                            <Badge variant="success" className="text-xs">Benign</Badge>
                          )}
                        </TableCell>
                        <TableCell>
                          <Badge variant={getDecisionColor(r.decision).includes("danger") ? "danger" : getDecisionColor(r.decision).includes("warning") ? "warning" : "success"}>
                            {r.decision}
                          </Badge>
                        </TableCell>
                        <TableCell className="font-mono text-text-secondary">{r.latency_ms}ms</TableCell>
                        {selectedRun.results![0].ground_truth && (
                          <TableCell>
                            <Badge variant={r.ground_truth === "benign" ? "success" : "danger"} className="text-xs">
                              {r.ground_truth}
                            </Badge>
                          </TableCell>
                        )}
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
              {selectedRun.results!.length > 100 && (
                <p className="text-sm text-text-muted mt-2">Showing 100 of {selectedRun.results!.length} results. Export to see all.</p>
              )}
            </CardContent>
          </Card>
        )}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-text">Batch Analysis</h1>
          <p className="text-text-secondary text-sm">Upload CSV/JSON files for bulk request analysis and model evaluation</p>
        </div>
        <Button variant="outline" size="sm" onClick={loadRuns}>
          <RefreshCw className="w-4 h-4" />
          Refresh
        </Button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card className="lg:col-span-2">
          <CardHeader>
            <h3 className="font-medium text-text flex items-center gap-2">
              <Upload className="w-5 h-5" />
              Upload Dataset
            </h3>
          </CardHeader>
          <CardContent className="space-y-4">
            <div
              className={cn(
                "border-2 border-dashed rounded-lg p-8 text-center transition-colors",
                dragActive ? "border-primary bg-primary-light" : "border-border hover:border-primary/50"
              )}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
            >
              <input
                type="file"
                accept=".csv,.json"
                className="hidden"
                id="batch-file"
                onChange={handleFileSelect}
              />
              <label htmlFor="batch-file" className="cursor-pointer">
                <FileText className="w-12 h-12 mx-auto text-text-muted mb-4" />
                <p className="font-medium text-text">Drag & drop CSV or JSON file</p>
                <p className="text-sm text-text-muted mt-1">or click to browse</p>
                <p className="text-xs text-text-muted mt-4">Max 100MB • CSV with headers: method,path,query,headers,body,source_ip,session_id,user_id,label?</p>
              </label>
            </div>

            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={hasLabels}
                onChange={(e) => setHasLabels(e.target.checked)}
                className="w-4 h-4 rounded border-border text-primary focus:ring-primary"
              />
              <span className="text-sm text-text">File includes ground truth labels (for evaluation metrics)</span>
            </label>

            <Button variant="primary" size="lg" className="w-full" onClick={() => document.getElementById("batch-file")?.click()} disabled={uploading}>
              {uploading ? (
                <>
                  <Upload className="w-4 h-4 animate-spin mr-2" />
                  Processing Batch Analysis...
                </>
              ) : (
                <>
                  <Upload className="w-4 h-4 mr-2" />
                  Analyze Custom File
                </>
              )}
            </Button>

            <div className="flex flex-col sm:flex-row gap-2 pt-2 border-t border-border">
              <Button
                variant="secondary"
                size="default"
                className="flex-1 text-xs"
                onClick={handleLoadSample}
                disabled={uploading}
              >
                <Play className="w-3.5 h-3.5 mr-1 text-primary" />
                1-Click Run Sample Dataset (50 items)
              </Button>
              <a
                href="/sample_waf_dataset.csv"
                download="sample_waf_dataset.csv"
                className="inline-flex items-center justify-center px-3 py-2 text-xs font-medium rounded-lg border border-border hover:bg-surface-hover transition-colors text-text"
              >
                <Download className="w-3.5 h-3.5 mr-1 text-text-secondary" />
                Download Sample CSV
              </a>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <h3 className="font-medium text-text flex items-center gap-2">
              <Database className="w-5 h-5" />
              Expected Format
            </h3>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="p-3 rounded bg-surface-hover font-mono text-xs overflow-x-auto">
              {`CSV:
method,path,query,headers,body,source_ip,session_id,user_id,label
GET,/search,q=test,{},"",127.0.0.1,session-1,user-1,benign
POST,/login,,{"content-type":"application/json"},"username=admin",127.0.0.1,session-2,user-2,sql_injection`}
            </div>
            <div className="p-3 rounded bg-surface-hover font-mono text-xs overflow-x-auto">
              {`JSON:
{
  "requests": [
    {"method": "GET", "path": "/search", "query": "q=test", "headers": {}, "body": "", "source_ip": "127.0.0.1", "label": "benign"},
    {"method": "POST", "path": "/login", "body": "username=admin", "source_ip": "127.0.0.1", "label": "sql_injection"}
  ]
}`}
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <h3 className="font-medium text-text flex items-center gap-2">
            <BarChart2 className="w-5 h-5" />
            Analysis History
          </h3>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Run ID</TableHead>
                  <TableHead>Dataset</TableHead>
                  <TableHead>Samples</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Threats</TableHead>
                  <TableHead>Blocked</TableHead>
                  <TableHead>Precision</TableHead>
                  <TableHead>Recall</TableHead>
                  <TableHead>F1</TableHead>
                  <TableHead>Started</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {runs.length > 0 ? (
                  runs.map((run) => (
                    <TableRow key={run.run_id}>
                      <TableCell className="font-mono text-text">{run.run_id}</TableCell>
                      <TableCell className="truncate max-w-xs">{run.dataset_name}</TableCell>
                      <TableCell className="font-mono text-text">{formatNumber(run.total_samples)}</TableCell>
                      <TableCell>
                        <Badge variant={run.status === "completed" ? "success" : "info"}>{run.status}</Badge>
                      </TableCell>
                      <TableCell className="font-mono text-warning">{run.threats_detected}</TableCell>
                      <TableCell className="font-mono text-danger">{run.blocked}</TableCell>
                      <TableCell className="font-mono text-text">{run.precision ? (run.precision * 100).toFixed(1) + "%" : "—"}</TableCell>
                      <TableCell className="font-mono text-text">{run.recall ? (run.recall * 100).toFixed(1) + "%" : "—"}</TableCell>
                      <TableCell className="font-mono text-primary">{run.f1 ? (run.f1 * 100).toFixed(1) + "%" : "—"}</TableCell>
                      <TableCell className="text-text-secondary">{new Date(run.started_at).toLocaleString()}</TableCell>
                      <TableCell>
                        <Button variant="ghost" size="icon" onClick={() => handleViewRun(run.run_id)}>
                          <Eye className="w-4 h-4" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))
                ) : (
                  <TableRow>
                    <TableCell colSpan={11} className="py-8 text-center text-text-muted">
                      No batch runs yet. Upload a dataset to start analysis.
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}