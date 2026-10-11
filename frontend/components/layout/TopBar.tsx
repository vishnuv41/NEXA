"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";
import { useAppStore } from "@/hooks/useAppStore";
import { Shield, ToggleLeft, ToggleRight, Wifi, WifiOff, Menu } from "lucide-react";

type WAFModeEnum = "enforce" | "shadow";

interface TopBarProps {
  wafMode: WAFModeEnum;
  onModeChange: (mode: WAFModeEnum) => void;
  isConnected: boolean;
}

export function TopBar({ wafMode, onModeChange, isConnected }: TopBarProps) {
  const [showModeMenu, setShowModeMenu] = useState(false);

  return (
    <header className="h-14 bg-surface border-b border-border flex items-center justify-between px-5 gap-4 sticky top-0 z-20 shadow-xs transition-colors duration-300">
      <div className="flex items-center gap-4 flex-1">
        <h1 className="text-base font-bold text-text hidden sm:block tracking-tight">
          NEXA Adaptive WAF
        </h1>
        <div className="hidden md:flex items-center gap-2 px-2.5 py-1 rounded-md bg-surface-hover border border-border text-xs text-text-secondary">
          <span className="font-mono font-semibold text-text">Local</span>
          <span className="text-text-muted">Environment</span>
        </div>
      </div>

      <div className="flex items-center gap-3">
        {/* Auto Traffic Indicator */}
        <div className="hidden sm:flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-50 border border-emerald-200 text-xs text-emerald-700 font-medium">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-500 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-600"></span>
          </span>
          <span className="font-mono text-[11px]">Auto-Traffic: 10s</span>
        </div>

        <div className="relative">
          <button
            onClick={() => setShowModeMenu(!showModeMenu)}
            className={cn(
              "anime-mode-indicator flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-sm font-semibold transition-all border",
              wafMode === "enforce"
                ? "bg-emerald-50 border-emerald-300 text-emerald-700 hover:bg-emerald-100/80 shadow-xs"
                : "bg-amber-50 border-amber-300 text-amber-800 hover:bg-amber-100/80 shadow-xs"
            )}
            aria-expanded={showModeMenu}
            aria-haspopup="menu"
          >
            <Shield className="w-4 h-4 shrink-0" />
            <span className="capitalize font-semibold">{wafMode} Mode</span>
            <Menu className="w-3.5 h-3.5 opacity-70" />
          </button>

          {showModeMenu && (
            <>
              <div
                className="fixed inset-0 z-20"
                onClick={() => setShowModeMenu(false)}
                aria-hidden="true"
              />
              <div className="absolute right-0 top-full mt-2 z-30 w-72 bg-surface border border-border rounded-xl shadow-xl p-2 space-y-1.5 card-mode-shadow">
                <button
                  onClick={() => {
                    onModeChange("enforce");
                    setShowModeMenu(false);
                  }}
                  className={cn(
                    "w-full text-left p-2.5 rounded-lg text-sm transition-colors",
                    wafMode === "enforce" ? "bg-emerald-50 border border-emerald-200" : "hover:bg-surface-hover border border-transparent"
                  )}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 font-semibold text-emerald-700">
                      <Shield className="w-4 h-4" />
                      <span>Enforce Mode</span>
                    </div>
                    {wafMode === "enforce" && <span className="text-[10px] bg-emerald-100 text-emerald-800 px-2 py-0.5 rounded font-mono font-bold">ACTIVE</span>}
                  </div>
                  <p className="text-xs text-text-secondary mt-1">Active protection: Malicious requests are denied (HTTP 403) and blocked upstream.</p>
                </button>

                <button
                  onClick={() => {
                    onModeChange("shadow");
                    setShowModeMenu(false);
                  }}
                  className={cn(
                    "w-full text-left p-2.5 rounded-lg text-sm transition-colors",
                    wafMode === "shadow" ? "bg-amber-50 border border-amber-200" : "hover:bg-surface-hover border border-transparent"
                  )}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 font-semibold text-amber-800">
                      <ToggleLeft className="w-4 h-4" />
                      <span>Shadow Mode</span>
                    </div>
                    {wafMode === "shadow" && <span className="text-[10px] bg-amber-100 text-amber-900 px-2 py-0.5 rounded font-mono font-bold">ACTIVE</span>}
                  </div>
                  <p className="text-xs text-text-secondary mt-1">Passive simulation: Evaluates & logs all threats without dropping or blocking traffic.</p>
                </button>
              </div>
            </>
          )}
        </div>

        <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-surface border border-border shadow-xs">
          <div
            className={cn(
              "w-2 h-2 rounded-full",
              isConnected ? "bg-success" : "bg-danger"
            )}
          />
          <span className="text-xs font-medium text-text-secondary">
            {isConnected ? "Live" : "Offline"}
          </span>
        </div>
      </div>
    </header>
  );
}