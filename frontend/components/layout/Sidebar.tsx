"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";
import { useAppStore } from "@/hooks/useAppStore";
import {
  LayoutDashboard,
  Activity,
  GitBranch,
  Globe,
  FlaskConical,
  Shield,
  Database,
  Cpu,
  WifiOff,
  Wifi,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";

const navigation = [
  { name: "Overview", id: "overview", icon: LayoutDashboard },
  { name: "Live Monitor", id: "live", icon: Activity },
  { name: "Sessions", id: "sessions", icon: GitBranch },
  { name: "App Context", id: "context", icon: Globe },
  { name: "Attack Lab", id: "attack-lab", icon: FlaskConical },
  { name: "Policies", id: "policies", icon: Shield },
  { name: "Batch Analysis", id: "batch", icon: Database },
  { name: "Models", id: "models", icon: Cpu },
];

type Page = "overview" | "live" | "sessions" | "context" | "attack-lab" | "policies" | "batch" | "models";

export function Sidebar({
  activePage,
  onPageChange,
}: {
  activePage: Page;
  onPageChange: (page: Page) => void;
}) {
  const [collapsed, setCollapsed] = useState(false);
  const isConnected = useAppStore((s) => s.isConnected);
  const wafStatus = useAppStore((s) => s.wafStatus);

  return (
    <aside
      className={cn(
        "flex flex-col bg-surface border-r border-border transition-all duration-200 shrink-0 shadow-xs",
        collapsed ? "w-16" : "w-64"
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between h-14 px-3.5 border-b border-border">
        {!collapsed && (
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-lg bg-primary/10 border border-primary/20 flex items-center justify-center text-primary shrink-0 shadow-xs">
              <Shield className="w-4 h-4" />
            </div>
            <span className="font-bold text-sm text-text tracking-tight">NEXA WAF</span>
          </div>
        )}
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="p-1.5 rounded-lg hover:bg-surface-hover transition-colors text-text-secondary hover:text-text"
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {collapsed ? (
            <ChevronRight className="w-4 h-4" />
          ) : (
            <ChevronLeft className="w-4 h-4" />
          )}
        </button>
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto py-3 px-2" aria-label="Main navigation">
        <ul className="space-y-0.5" role="list">
          {navigation.map((item) => {
            const isActive = activePage === item.id;
            return (
              <li key={item.id}>
                <button
                  onClick={() => onPageChange(item.id as Page)}
                  className={cn(
                    "w-full flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-150",
                    collapsed ? "justify-center" : "",
                    isActive
                      ? "bg-primary/8 text-primary border border-primary/15 shadow-xs"
                      : "text-text-secondary hover:bg-surface-hover hover:text-text border border-transparent"
                  )}
                  aria-current={isActive ? "page" : undefined}
                  title={collapsed ? item.name : undefined}
                >
                  <item.icon
                    className={cn(
                      "w-4 h-4 shrink-0",
                      isActive ? "text-primary" : "text-text-muted"
                    )}
                    aria-hidden="true"
                  />
                  {!collapsed && <span>{item.name}</span>}
                </button>
              </li>
            );
          })}
        </ul>
      </nav>

      {/* Footer status */}
      <div className="border-t border-border p-3 space-y-2">
        {!collapsed && (
          <>
            <div className="flex items-center gap-2 px-2 py-1">
              {isConnected ? (
                <Wifi className="w-3.5 h-3.5 text-success shrink-0" />
              ) : (
                <WifiOff className="w-3.5 h-3.5 text-text-muted shrink-0" />
              )}
              <span className={cn("text-xs font-medium", isConnected ? "text-success" : "text-text-muted")}>
                {isConnected ? "Connected" : "Disconnected"}
              </span>
            </div>
            <div className="px-2 py-1">
              <div className="text-[10px] uppercase tracking-wider text-text-muted font-semibold mb-1.5">WAF Status</div>
              <div className="flex items-center gap-2">
                <div className={cn(
                  "w-1.5 h-1.5 rounded-full shrink-0",
                  wafStatus === "protected" ? "bg-success" : wafStatus === "warning" ? "bg-warning" : "bg-text-muted"
                )} />
                <span className="text-xs text-text-secondary capitalize">{wafStatus ?? "Protected"}</span>
              </div>
            </div>
          </>
        )}
        {collapsed && (
          <div className="flex justify-center">
            {isConnected ? (
              <Wifi className="w-4 h-4 text-success" />
            ) : (
              <WifiOff className="w-4 h-4 text-text-muted" />
            )}
          </div>
        )}
      </div>
    </aside>
  );
}