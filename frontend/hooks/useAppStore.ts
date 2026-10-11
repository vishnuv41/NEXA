import { create } from "zustand";
import { persist } from "zustand/middleware";
import { WAFModeEnum, DecisionEnum, ThreatTypeEnum, Policy, StatsSummary } from "@/types/api";

export interface RequestEvent {
  id?: number;
  request_id: string;
  timestamp: string;
  method: string;
  path: string;
  query?: string;
  query_string?: string | null;
  source_ip: string;
  session_id: string | null;
  user_id?: string | null;
  status_code?: number | null;
  latency_ms: number;
  transformer_score?: number | null;
  anomaly_score?: number | null;
  session_score?: number | null;
  application_score?: number | null;
  rule_score?: number | null;
  final_risk_score: number;
  risk_score: number;
  attack_type: ThreatTypeEnum | null;
  decision: DecisionEnum;
  decision_reason?: string | null;
  signals?: Record<string, number>;
  body_summary?: string;
}

export interface Session {
  id?: number;
  session_key: string;
  source_ip: string;
  user_identifier?: string | null;
  started_at?: string;
  last_seen_at?: string;
  request_count: number;
  risk_score: number;
  anomaly_score: number;
  current_state?: string | null;
  endpoint_count?: number;
  endpoint_sequence: Array<{ endpoint: string; timestamp: string; risk: number; decision?: DecisionEnum }>;
  risk_timeline: Array<{ timestamp: string; risk_score: number; decision: string }>;
}

interface AppState {
  // Connection
  isConnected: boolean;
  setConnected: (connected: boolean) => void;

  // WAF Mode
  wafMode: WAFModeEnum;
  setWafMode: (mode: WAFModeEnum) => void;

  // Live events
  liveEvents: RequestEvent[];
  setLiveEvents: (events: RequestEvent[]) => void;
  addLiveEvent: (event: any) => void;
  clearLiveEvents: () => void;

  // Sessions
  sessions: Session[];
  setSessions: (sessions: Session[]) => void;

  // Stats
  stats: StatsSummary | null;
  setStats: (stats: any) => void;

  // Policy
  policy: Policy | null;
  setPolicy: (policy: any) => void;

  // WAF Status label (protected/warning/offline)
  wafStatus: string;
  setWafStatus: (status: string) => void;
}

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      isConnected: false,
      setConnected: (connected) => set({ isConnected: connected }),

      wafMode: "enforce",
      setWafMode: (mode) => set({ wafMode: mode }),

      liveEvents: [],
      setLiveEvents: (events) => set({ liveEvents: events }),
      addLiveEvent: (event) =>
        set((state) => {
          if (event.request_id && state.liveEvents.some((e) => e.request_id === event.request_id)) {
            return state;
          }
          const final_risk_score = event.final_risk_score ?? event.risk_score ?? 0;
          const risk_score = event.risk_score ?? event.final_risk_score ?? 0;
          return {
            liveEvents: [
              { ...event, final_risk_score, risk_score },
              ...state.liveEvents,
            ].slice(0, 500),
          };
        }),
      clearLiveEvents: () => set({ liveEvents: [] }),

      sessions: [],
      setSessions: (sessions) => set({ sessions }),

      stats: null,
      setStats: (stats) => set({ stats }),

      policy: null,
      setPolicy: (policy) => set({ policy }),

      wafStatus: "protected",
      setWafStatus: (status) => set({ wafStatus: status }),
    }),
    {
      name: "waf-app-store",
      partialize: (state) => ({
        wafMode: state.wafMode,
      }),
    }
  )
);