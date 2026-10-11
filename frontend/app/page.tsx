"use client";

import { useState, useEffect } from "react";
import { Sidebar } from "@/components/layout/Sidebar";
import { TopBar } from "@/components/layout/TopBar";
import { OverviewPage } from "@/components/pages/OverviewPage";
import { LiveMonitorPage } from "@/components/pages/LiveMonitorPage";
import { SessionsPage } from "@/components/pages/SessionsPage";
import { AppContextPage } from "@/components/pages/AppContextPage";
import { AttackLabPage } from "@/components/pages/AttackLabPage";
import { PoliciesPage } from "@/components/pages/PoliciesPage";
import { BatchAnalysisPage } from "@/components/pages/BatchAnalysisPage";
import { ModelsPage } from "@/components/pages/ModelsPage";
import { useAppStore } from "@/hooks/useAppStore";
import { useSSE } from "@/hooks/useSSE";
import { api } from "@/lib/api";
import { animatePageTransition, animateModeSwitch } from "@/lib/animations";

type Page = "overview" | "live" | "sessions" | "context" | "attack-lab" | "policies" | "batch" | "models";

const VALID_PAGES: Page[] = ["overview", "live", "sessions", "context", "attack-lab", "policies", "batch", "models"];

function getPageFromPath(path: string): Page {
  const clean = path.replace(/^\//, "").split("/")[0] as Page;
  return VALID_PAGES.includes(clean) ? clean : "overview";
}

const AUTO_TRAFFIC_POOL = [
  // Legitimate requests
  { method: "GET", path: "/", query: "", body: "", headers: { "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0" }, source_ip: "192.168.1.10" },
  { method: "GET", path: "/products", query: "", body: "", headers: { "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari/605.1" }, source_ip: "10.0.0.15" },
  { method: "GET", path: "/products/1", query: "", body: "", headers: { "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Firefox/122.0" }, source_ip: "172.16.0.22" },
  { method: "GET", path: "/search", query: "q=ultrabook", body: "", headers: { "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) Mobile" }, source_ip: "203.0.113.8" },
  { method: "GET", path: "/dashboard", query: "", body: "", headers: { "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0" }, source_ip: "192.168.1.45" },
  { method: "GET", path: "/products/2", query: "", body: "", headers: { "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0" }, source_ip: "10.0.0.50" },

  // Attack requests (various families)
  { method: "GET", path: "/search", query: "q=' OR '1'='1' --", body: "", headers: { "User-Agent": "sqlmap/1.7.8#stable" }, source_ip: "185.220.101.5" },
  { method: "GET", path: "/products/1", query: "id=1 UNION SELECT null,username,password FROM users--", body: "", headers: { "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)" }, source_ip: "198.51.100.23" },
  { method: "GET", path: "/search", query: "q=<script>alert('waf_xss_probe')</script>", body: "", headers: { "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)" }, source_ip: "185.220.101.5" },
  { method: "GET", path: "/products/../../../etc/passwd", query: "", body: "", headers: { "User-Agent": "Nikto/2.1.6" }, source_ip: "45.33.32.156" },
  { method: "GET", path: "/search", query: "q=; cat /etc/passwd", body: "", headers: { "User-Agent": "curl/7.68.0" }, source_ip: "185.220.101.5" },
  { method: "GET", path: "/products/1", query: "id=1; DROP TABLE users--", body: "", headers: { "User-Agent": "sqlmap/1.7.8" }, source_ip: "185.220.101.5" },
];

export default function Dashboard() {
  useSSE();
  const [activePage, setActivePage] = useState<Page>("overview");
  const { wafMode, setWafMode, isConnected, addLiveEvent, setStats } = useAppStore();

  // Sync data-waf-mode with root HTML element for global theme variables
  useEffect(() => {
    if (typeof document !== "undefined") {
      document.documentElement.setAttribute("data-waf-mode", wafMode);
      document.body.setAttribute("data-waf-mode", wafMode);
    }
    animateModeSwitch();
  }, [wafMode]);

  // Load and synchronize initial WAF mode from backend
  useEffect(() => {
    api.waf.getMode().then((data) => {
      if (data?.mode) {
        setWafMode(data.mode as any);
      }
    }).catch(() => {});
  }, [setWafMode]);

  const handleModeChange = async (mode: "enforce" | "shadow") => {
    setWafMode(mode);
    animateModeSwitch();
    try {
      await api.waf.setMode(mode);
    } catch (e) {
      console.error("Failed to update WAF mode on backend:", e);
    }
  };

  // Automatically post a request every 10 seconds (alternating threats and normal)
  useEffect(() => {
    let index = 0;
    const postAutoTraffic = async () => {
      const item = AUTO_TRAFFIC_POOL[index % AUTO_TRAFFIC_POOL.length];
      index++;
      try {
        const res = await api.waf.inspectAndProxy(item);
        if (res) {
          const risk = res.risk_score ?? 0;
          addLiveEvent({
            request_id: res.request_id || `auto-${Date.now()}`,
            timestamp: new Date().toISOString(),
            method: item.method,
            path: item.path,
            query: item.query,
            source_ip: item.source_ip,
            session_id: `ip:${item.source_ip}`,
            risk_score: risk,
            final_risk_score: risk,
            attack_type: res.attack_type ?? null,
            decision: res.decision ?? "allow",
            latency_ms: 15,
          });

          // Refresh overview summary stats to update charts & counters
          api.events.getSummary().then((s) => {
            if (s) setStats(s as any);
          }).catch(() => {});
        }
      } catch (err) {
        // Ignore background network blips
      }
    };

    const firstRun = setTimeout(postAutoTraffic, 2000);
    const interval = setInterval(postAutoTraffic, 10000);

    return () => {
      clearTimeout(firstRun);
      clearInterval(interval);
    };
  }, [addLiveEvent, setStats]);

  useEffect(() => {
    if (typeof window !== "undefined") {
      const initial = getPageFromPath(window.location.pathname);
      setActivePage(initial);

      const handlePopState = () => {
        setActivePage(getPageFromPath(window.location.pathname));
      };
      window.addEventListener("popstate", handlePopState);
      return () => window.removeEventListener("popstate", handlePopState);
    }
  }, []);

  const handlePageChange = (page: Page) => {
    setActivePage(page);
    if (typeof window !== "undefined") {
      const url = page === "overview" ? "/" : `/${page}`;
      if (window.location.pathname !== url) {
        window.history.pushState({}, "", url);
      }
    }
  };

  useEffect(() => {
    animatePageTransition(".anime-page-transition");
  }, [activePage]);

  const pages = {
    overview: <OverviewPage />,
    live: <LiveMonitorPage />,
    sessions: <SessionsPage />,
    context: <AppContextPage />,
    "attack-lab": <AttackLabPage />,
    policies: <PoliciesPage />,
    batch: <BatchAnalysisPage />,
    models: <ModelsPage />,
  };

  return (
    <div className="flex h-screen overflow-hidden bg-bg text-text transition-colors duration-500" data-waf-mode={wafMode}>
      <Sidebar activePage={activePage} onPageChange={handlePageChange} />
      <div className="flex-1 flex flex-col overflow-hidden">
        <TopBar wafMode={wafMode} onModeChange={handleModeChange} isConnected={isConnected} />
        <main className="flex-1 overflow-auto p-4 md:p-6 transition-colors duration-500">
          <div key={activePage} className="anime-page-transition">
            {pages[activePage]}
          </div>
        </main>
      </div>
    </div>
  );
}