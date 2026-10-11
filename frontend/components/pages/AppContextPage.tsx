"use client";

import { useEffect, useState } from "react";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader } from "@/components/ui/Card";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "@/components/ui/Table";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Separator } from "@/components/ui/Separator";
import {
  Globe,
  Shield,
  Key,
  Download,
  Upload,
  RefreshCw,
  FileJson,
  Search,
  Eye,
  AlertTriangle,
} from "lucide-react";
import { formatNumber, getRiskColor, getRiskBg, truncate } from "@/lib/utils";
import { EndpointProfile, SensitivityEnum } from "@/types/api";

export function AppContextPage() {
  const [endpoints, setEndpoints] = useState<EndpointProfile[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [importing, setImporting] = useState(false);
  const [importFile, setImportFile] = useState<File | null>(null);

  useEffect(() => {
    loadEndpoints();
  }, []);

  const loadEndpoints = async () => {
    try {
      const data = await api.context.getEndpoints();
      setEndpoints(data);
      setLoading(false);
    } catch (e) {
      console.error("Failed to load endpoints:", e);
      setLoading(false);
    }
  };

  const handleImport = async () => {
    if (!importFile) return;
    setImporting(true);
    try {
      await api.context.importOpenAPIFile(importFile);
      await loadEndpoints();
      setImportFile(null);
    } catch (e) {
      console.error("Failed to import OpenAPI:", e);
    }
    setImporting(false);
  };

  const handleSensitivityChange = async (id: number, sensitivity: SensitivityEnum) => {
    try {
      await api.context.updateSensitivity(id, sensitivity);
      await loadEndpoints();
    } catch (e) {
      console.error("Failed to update sensitivity:", e);
    }
  };

  const filteredEndpoints = endpoints.filter((ep) => {
    if (!search) return true;
    const s = search.toLowerCase();
    return ep.path_template.toLowerCase().includes(s) ||
      ep.method.toLowerCase().includes(s) ||
      ep.sensitivity_level.toLowerCase().includes(s);
  });

  const sensitivityColors: Record<SensitivityEnum, "success" | "info" | "warning" | "danger"> = {
    low: "success",
    medium: "info",
    high: "warning",
    critical: "danger",
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-text">Application Context</h1>
          <p className="text-text-secondary text-sm">OpenAPI-driven endpoint contracts and sensitivity levels</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={loadEndpoints}>
            <RefreshCw className="w-4 h-4" />
            Refresh
          </Button>
          <label className="btn-secondary flex items-center gap-2" htmlFor="openapi-file">
            <Upload className="w-4 h-4" />
            Import OpenAPI
            <input
              id="openapi-file"
              type="file"
              accept=".json,.yaml,.yml"
              className="hidden"
              onChange={(e) => setImportFile(e.target.files?.[0] || null)}
            />
          </label>
        </div>
      </div>

      {importFile && (
        <Card className="bg-info-light border-info">
          <CardContent className="p-4 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <FileJson className="w-5 h-5 text-info" />
              <div>
                <p className="font-medium text-info">Ready to import</p>
                <p className="text-sm text-info/80">{importFile.name} ({(importFile.size / 1024).toFixed(1)} KB)</p>
              </div>
            </div>
            <div className="flex gap-2">
              <Button variant="primary" size="sm" onClick={handleImport} disabled={importing}>
                {importing ? "Importing..." : "Import"}
              </Button>
              <Button variant="ghost" size="sm" onClick={() => setImportFile(null)}>
                Cancel
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardContent className="p-4">
          <div className="relative max-w-md mb-4">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted" />
            <input
              type="text"
              placeholder="Search endpoints..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="input pl-10"
            />
          </div>

          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Endpoint</TableHead>
                  <TableHead>Method</TableHead>
                  <TableHead>Params</TableHead>
                  <TableHead>Auth Required</TableHead>
                  <TableHead>Sensitivity</TableHead>
                  <TableHead>Content Types</TableHead>
                  <TableHead className="text-right">Requests</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {loading ? (
                  <TableRow>
                    <TableCell colSpan={8} className="py-8 text-center text-text-muted">Loading endpoints...</TableCell>
                  </TableRow>
                ) : filteredEndpoints.length > 0 ? (
                  filteredEndpoints.map((ep, i) => (
                    <TableRow key={i}>
                      <TableCell className="font-mono text-text truncate max-w-md" title={ep.path_template}>
                        {ep.path_template}
                      </TableCell>
                      <TableCell>
                        <span className="font-mono text-text bg-surface-hover px-1.5 py-0.5 rounded">
                          {ep.method}
                        </span>
                      </TableCell>
                      <TableCell className="text-text-secondary">
                        {ep.expected_parameters?.parameters?.length || 0}
                      </TableCell>
                      <TableCell>
                        {ep.authentication_required ? (
                          <span className="flex items-center gap-1 text-success text-sm">
                            <Key className="w-3 h-3" />
                            Yes
                          </span>
                        ) : (
                          <span className="text-text-muted">No</span>
                        )}
                      </TableCell>
                      <TableCell>
                        <Badge variant={sensitivityColors[ep.sensitivity_level]} className="text-xs">
                          {ep.sensitivity_level}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-text-secondary truncate max-w-xs">
                        {ep.allowed_content_types?.join(", ") || "—"}
                      </TableCell>
                      <TableCell className="text-right font-mono text-text">{formatNumber(ep.request_count)}</TableCell>
                      <TableCell>
                        <div className="flex items-center gap-1">
                          <select
                            value={ep.sensitivity_level}
                            onChange={(e) => handleSensitivityChange(ep.id, e.target.value as SensitivityEnum)}
                            className="input py-1 px-2 text-xs w-auto"
                          >
                            <option value="low">Low</option>
                            <option value="medium">Medium</option>
                            <option value="high">High</option>
                            <option value="critical">Critical</option>
                          </select>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))
                ) : (
                  <TableRow>
                    <TableCell colSpan={8} className="py-8 text-center text-text-muted">
                      No endpoints found. Import an OpenAPI specification to get started.
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card>
          <CardHeader>
            <h3 className="font-medium text-text flex items-center gap-2">
              <Globe className="w-5 h-5" />
              Endpoint Summary
            </h3>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div className="flex justify-between">
                <span className="text-text-secondary">Total Endpoints</span>
                <span className="font-mono text-text">{endpoints.length}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-text-secondary">Authenticated</span>
                <span className="font-mono text-text">{endpoints.filter(e => e.authentication_required).length}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-text-secondary">Public</span>
                <span className="font-mono text-text">{endpoints.filter(e => !e.authentication_required).length}</span>
              </div>
              <Separator />
              {(["critical", "high", "medium", "low"] as SensitivityEnum[]).map((level) => (
                <div key={level} className="flex justify-between">
                  <span className="flex items-center gap-2">
                    <Badge variant={sensitivityColors[level]} className="text-xs">
                      {level}
                    </Badge>
                  </span>
                  <span className="font-mono text-text">{endpoints.filter(e => e.sensitivity_level === level).length}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <h3 className="font-medium text-text flex items-center gap-2">
              <Shield className="w-5 h-5" />
              Security Posture
            </h3>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div className="flex items-center gap-2 p-3 rounded-lg bg-success-light/50">
                <Shield className="w-5 h-5 text-success" />
                <div>
                  <p className="font-medium text-text">Contract Validation Active</p>
                  <p className="text-sm text-text-secondary">Requests validated against OpenAPI spec</p>
                </div>
              </div>
              <div className="flex items-center gap-2 p-3 rounded-lg bg-info-light/50">
                <Key className="w-5 h-5 text-info" />
                <div>
                  <p className="font-medium text-text">Auth Enforcement</p>
                  <p className="text-sm text-text-secondary">{endpoints.filter(e => e.authentication_required).length} endpoints require authentication</p>
                </div>
              </div>
              <div className="flex items-center gap-2 p-3 rounded-lg bg-warning-light/50">
                <AlertTriangle className="w-5 h-5 text-warning" />
                <div>
                  <p className="font-medium text-text">High Sensitivity Endpoints</p>
                  <p className="text-sm text-text-secondary">{endpoints.filter(e => e.sensitivity_level === "critical" || e.sensitivity_level === "high").length} endpoints flagged</p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <h3 className="font-medium text-text flex items-center gap-2">
              <Download className="w-5 h-5" />
              Export Contract
            </h3>
          </CardHeader>
          <CardContent>
            <p className="text-text-secondary text-sm mb-4">Export current endpoint configuration for backup or sharing.</p>
            <Button variant="outline" className="w-full" onClick={() => {
              const blob = new Blob([JSON.stringify(endpoints, null, 2)], { type: "application/json" });
              const url = URL.createObjectURL(blob);
              const a = document.createElement("a");
              a.href = url;
              a.download = `waf-endpoints-${Date.now()}.json`;
              a.click();
              URL.revokeObjectURL(url);
            }}>
              <Download className="w-4 h-4" />
              Download JSON
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}