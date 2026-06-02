// Types for the Signal Dashboard design integration.
//
// IMPORTANT (Brutal Truth):
// - Backend responses are truth-wrapped ({truth, data}).
// - Do not invent fields: when a field is not emitted by backend, keep it optional
//   and render explicit empty states in UI.

export type NavigationTab =
  | "signals"
  | "market"  // Replaces 'session' placeholder logic
  | "journal"
  | "outlook"
  | "errors"  // Replaces 'system' placeholder logic
  | "strategy" // Strategy Health
  | "news"    // Was 'ai' or 'system' before
  | "controls";

export type RunnerStatus = "RUNNING" | "STOPPED" | "ERROR" | "UNKNOWN";

export interface SystemHealth {
  status: RunnerStatus;
  mode: string | null;
  cycleLatencyMs: number | null;
  lastHeartbeat: string | null;
  version: string | null;
  // Backend does not currently emit a dedicated "triple lock" boolean on /api/status.
  // Keep this nullable and let UI show an explicit unknown state.
  safetyLock: "LOCKED" | "UNLOCKED" | "UNKNOWN";
  noTradeReason?: string | null;
  weekend?: boolean;
}

export interface Wrapped<T> {
  truth?: unknown;
  data?: T;
}

export interface StatusData {
  system_alive?: boolean;
  system_label?: string;
  mode?: string;
  last_scan_at?: string | null;
  last_status_write_at?: string | null;
  last_signals_generated?: number;
  execution_enabled?: boolean;
  readiness_score?: number;
  readiness_countdown?: unknown;
  effective_guards?: Array<Record<string, unknown>>;
  no_trade_reason?: string | null;
  weekend_indicator?: boolean;
  // ... keep permissive; UI must handle missing keys gracefully.
  [k: string]: unknown;
}

export interface SignalsData {
  ok?: boolean;
  signals?: Array<Record<string, unknown>>;
  count?: number | null;
  used_path?: string;
  newest_ts_utc?: string;
  [k: string]: unknown;
}

export interface JournalTradesData {
  ok?: boolean;
  trades?: Array<Record<string, unknown>>;
  total?: number;
  limit?: number;
  offset?: number;
  [k: string]: unknown;
}

export interface NewsData {
  ok?: boolean;
  news?: Array<Record<string, unknown>>;
  provider_status?: Record<string, unknown>; // For /api/news/status integration
  [k: string]: unknown;
}

export interface OutlookData {
  ok?: boolean;
  horizon?: "daily" | "weekly" | "monthly";
  outlook?: Record<string, unknown> | null;
  [k: string]: unknown;
}

export interface MarketData {
  instruments?: Array<{
    instrument: string;
    mid?: number;
    time?: string;
    regime?: {
      regime: string;
      adx?: number;
    };
  }>;
  ts_utc?: string;
  [k: string]: unknown;
}

export interface ErrorData {
  overall_status?: string;
  top_blocker?: string | null;
  latest_events?: Array<{
    severity: string;
    message: string;
    hint_cmd?: string;
    ts?: string;
  }>;
  [k: string]: unknown;
}
