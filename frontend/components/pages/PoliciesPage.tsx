"use client";

import { useEffect, useState } from "react";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Badge } from "@/components/ui/Badge";
import { Progress } from "@/components/ui/Progress";
import { Separator } from "@/components/ui/Separator";
import { useAppStore } from "@/hooks/useAppStore";
import {
  Shield,
  ToggleLeft,
  ToggleRight,
  SlidersHorizontal,
  Save,
  RefreshCw,
  AlertTriangle,
  Check,
  X,
} from "lucide-react";
import { WAFModeEnum, PolicyThresholds, PolicyWeights, Policy } from "@/types/api";

export function PoliciesPage() {
  const { wafMode, setWafMode, policy, setPolicy } = useAppStore();
  const [thresholds, setThresholds] = useState<PolicyThresholds>({
    allow: 0.2,
    monitor: 0.45,
    rate_limit: 0.65,
    challenge: 0.85,
    block: 1.0,
  });
  const [weights, setWeights] = useState<PolicyWeights>({
    transformer: 0.35,
    anomaly: 0.15,
    session: 0.2,
    application: 0.2,
    rules: 0.1,
  });
  const [saving, setSaving] = useState(false);
  const [mode, setMode] = useState<WAFModeEnum>("enforce");

  useEffect(() => {
    loadPolicy();
  }, []);

  useEffect(() => {
    if (wafMode) {
      setMode(wafMode);
    }
  }, [wafMode]);

  const loadPolicy = async () => {
    try {
      const data = await api.waf.getPolicy();
      setPolicy(data);
      setThresholds(data.thresholds);
      setWeights(data.weights);
      setMode(data.mode);
      setWafMode(data.mode);
    } catch (e) {
      console.error("Failed to load policy:", e);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await api.waf.updatePolicy({ thresholds, weights, mode });
      await api.waf.setMode(mode);
      setPolicy({ mode, thresholds, weights });
      setWafMode(mode);
    } catch (e) {
      console.error("Failed to save policy:", e);
    }
    setSaving(false);
  };

  const handleModeChange = async (newMode: WAFModeEnum) => {
    setMode(newMode);
    setWafMode(newMode);
    try {
      await api.waf.setMode(newMode);
    } catch (e) {
      console.error("Failed to update WAF mode:", e);
    }
  };

  const thresholdConfig = [
    { key: "allow", label: "Allow", description: "Request passes without flags", color: "success" },
    { key: "monitor", label: "Monitor", description: "Request logged for review", color: "info" },
    { key: "rate_limit", label: "Rate Limit", description: "Request throttled", color: "warning" },
    { key: "challenge", label: "Challenge", description: "Verification required", color: "warning" },
    { key: "block", label: "Block", description: "Request denied", color: "danger" },
  ] as const;

  const weightConfig = [
    { key: "transformer", label: "Transformer", description: "ML classifier probability", icon: "Brain" },
    { key: "anomaly", label: "Anomaly", description: "Model uncertainty score", icon: "AlertTriangle" },
    { key: "session", label: "Session", description: "Behavioral analysis", icon: "Users" },
    { key: "application", label: "Application", description: "Contract validation", icon: "Globe" },
    { key: "rules", label: "Rules", description: "Deterministic signatures", icon: "Shield" },
  ] as const;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-text">Policies</h1>
          <p className="text-text-secondary text-sm">Configure WAF enforcement mode, risk thresholds, and signal weights</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={loadPolicy}>
            <RefreshCw className="w-4 h-4" />
            Refresh
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card className="lg:col-span-2">
          <CardHeader className="flex items-center justify-between">
            <h3 className="font-medium text-text flex items-center gap-2">
              <SlidersHorizontal className="w-5 h-5" />
              Risk Thresholds
            </h3>
            <Badge variant={mode === "enforce" ? "success" : "warning"}>
              {mode === "enforce" ? "Enforce" : "Shadow"} Mode
            </Badge>
          </CardHeader>
          <CardContent className="space-y-6">
            <div>
              <label className="block text-sm font-semibold text-text mb-3">Enforcement Mode</label>
              <div className="flex items-center gap-4">
                <label className={cn(
                  "flex items-center gap-3 px-4 py-3 rounded-xl border transition-all cursor-pointer flex-1 shadow-xs",
                  mode === "enforce"
                    ? "border-emerald-500 bg-emerald-50/70 ring-1 ring-emerald-500/20"
                    : "border-border hover:border-emerald-500/40 bg-surface"
                )}>
                  <input
                    type="radio"
                    name="mode"
                    value="enforce"
                    checked={mode === "enforce"}
                    onChange={() => handleModeChange("enforce")}
                    className="sr-only"
                  />
                  <div className="p-2 rounded-lg bg-emerald-100/60 text-emerald-700">
                    <Shield className="w-5 h-5" />
                  </div>
                  <div>
                    <div className="font-semibold text-text">Enforce</div>
                    <div className="text-xs text-text-secondary">Block, challenge, and rate-limit requests</div>
                  </div>
                </label>
                <label className={cn(
                  "flex items-center gap-3 px-4 py-3 rounded-xl border transition-all cursor-pointer flex-1 shadow-xs",
                  mode === "shadow"
                    ? "border-amber-500 bg-amber-50/70 ring-1 ring-amber-500/20"
                    : "border-border hover:border-amber-500/40 bg-surface"
                )}>
                  <input
                    type="radio"
                    name="mode"
                    value="shadow"
                    checked={mode === "shadow"}
                    onChange={() => handleModeChange("shadow")}
                    className="sr-only"
                  />
                  <div className="p-2 rounded-lg bg-amber-100/60 text-amber-800">
                    <ToggleLeft className="w-5 h-5" />
                  </div>
                  <div>
                    <div className="font-semibold text-text">Shadow</div>
                    <div className="text-xs text-text-secondary">Log decisions but allow all requests</div>
                  </div>
                </label>
              </div>
            </div>

            <Separator />

            <div>
              <label className="block text-sm font-medium text-text mb-3">Risk Score Thresholds</label>
              <p className="text-sm text-text-secondary mb-4">
                Requests are classified by their final risk score. Adjust thresholds to tune sensitivity.
              </p>
              <div className="space-y-4">
                {thresholdConfig.map((t, i) => (
                  <div key={t.key} className="space-y-2">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Badge variant={t.color as any} className="text-xs">{t.label}</Badge>
                        <span className="text-sm text-text-secondary">{t.description}</span>
                      </div>
                      <span className="font-mono text-text">
                        {(thresholds[t.key as keyof PolicyThresholds] * 100).toFixed(0)}%
                      </span>
                    </div>
                    <input
                      type="range"
                      min={i === 0 ? 0 : (thresholds[thresholdConfig[i - 1].key as keyof PolicyThresholds] * 100)}
                      max={t.key === "block" ? 100 : 100}
                      value={thresholds[t.key as keyof PolicyThresholds] * 100}
                      onChange={(e) => setThresholds(prev => ({
                        ...prev,
                        [t.key]: Number(e.target.value) / 100,
                      }))}
                      className="w-full h-2 bg-surface-hover rounded-lg appearance-none accent-primary"
                    />
                    <div className="flex justify-between text-xs text-text-muted">
                      <span>{i === 0 ? "0%" : `${(thresholds[thresholdConfig[i - 1].key as keyof PolicyThresholds] * 100).toFixed(0)}%`}</span>
                      <span>{t.key === "block" ? "100%" : "100%"}</span>
                    </div>
                  </div>
                ))}
              </div>

              <div className="h-8 flex items-end gap-1 px-2 mt-4">
                {thresholdConfig.map((t, i) => (
                  <div
                    key={t.key}
                    className="flex-1 rounded-t transition-all duration-200"
                    style={{
                      height: `${Math.max((thresholds[t.key as keyof PolicyThresholds] - (i === 0 ? 0 : thresholds[thresholdConfig[i - 1].key as keyof PolicyThresholds])) * 100, 4)}%`,
                      backgroundColor: `var(--color-${t.color})`,
                      opacity: 0.3,
                    }}
                    title={`${t.label}: ${(thresholds[t.key as keyof PolicyThresholds] * 100).toFixed(0)}%`}
                  />
                ))}
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <h3 className="font-medium text-text flex items-center gap-2">
              <Shield className="w-5 h-5" />
              Current Mode
            </h3>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className={cn(
              "p-5 rounded-xl text-center border transition-all duration-300",
              mode === "enforce" ? "bg-emerald-50/80 border-emerald-200" : "bg-amber-50/80 border-amber-200"
            )}>
              <div className={cn("text-3xl font-extrabold tracking-tight", mode === "enforce" ? "text-emerald-700" : "text-amber-800")}>
                {mode.toUpperCase()}
              </div>
              <div className="text-xs text-text-secondary mt-1 font-medium">
                {mode === "enforce" ? "Active blocking enabled (403)" : "Monitoring only - zero blocking"}
              </div>
            </div>
            <Button
              variant={mode === "enforce" ? "outline" : "primary"}
              className="w-full font-semibold"
              onClick={() => handleModeChange(mode === "enforce" ? "shadow" : "enforce")}
            >
              {mode === "enforce" ? (
                <>
                  <ToggleLeft className="w-4 h-4 text-amber-600" />
                  Switch to Shadow Mode
                </>
              ) : (
                <>
                  <Shield className="w-4 h-4" />
                  Switch to Enforce Mode
                </>
              )}
            </Button>
            <p className="text-xs text-text-muted text-center">
              {mode === "enforce"
                ? "Requests exceeding block threshold will be denied"
                : "All requests allowed; decisions logged for analysis"}
            </p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <h3 className="font-medium text-text flex items-center gap-2">
            <SlidersHorizontal className="w-5 h-5" />
            Signal Weights
          </h3>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-text-secondary">
            Weights determine how much each signal contributes to the final risk score. Must sum to 100%.
          </p>
          <div className="space-y-4">
            {weightConfig.map((w) => (
              <div key={w.key} className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-medium text-text capitalize">{w.label}</span>
                  <span className="font-mono text-text">
                    {(weights[w.key as keyof PolicyWeights] * 100).toFixed(0)}%
                  </span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={weights[w.key as keyof PolicyWeights] * 100}
                  onChange={(e) => {
                    const newValue = Number(e.target.value) / 100;
                    setWeights(prev => {
                      // Normalize other weights to maintain sum = 1
                      const otherKeys = Object.keys(prev).filter(k => k !== w.key);
                      const otherSum = otherKeys.reduce((sum, k) => sum + prev[k as keyof PolicyWeights], 0);
                      const remaining = 1 - newValue;
                      const newWeights = { ...prev, [w.key]: newValue } as PolicyWeights;
                      if (otherSum > 0) {
                        otherKeys.forEach(k => {
                          newWeights[k as keyof PolicyWeights] = (prev[k as keyof PolicyWeights] / otherSum) * remaining;
                        });
                      }
                      return newWeights;
                    });
                  }}
                  className="w-full h-2 bg-surface-hover rounded-lg appearance-none accent-primary"
                />
              </div>
            ))}
          </div>
          <div className="flex items-center justify-between text-sm text-text-secondary pt-4 border-t border-border">
            <span>Total Weight</span>
            <span className="font-mono text-text">
              {(Object.values(weights).reduce((a, b) => a + b, 0) * 100).toFixed(1)}%
            </span>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex items-center justify-between">
          <h3 className="font-medium text-text">Actions</h3>
          <Button variant="primary" onClick={handleSave} disabled={saving}>
            <Save className="w-4 h-4" />
            {saving ? "Saving..." : "Save Policy"}
          </Button>
        </CardHeader>
        <CardContent>
          <div className="flex gap-2">
            <Button variant="outline" onClick={loadPolicy}>
              <RefreshCw className="w-4 h-4" />
              Reset to Defaults
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}