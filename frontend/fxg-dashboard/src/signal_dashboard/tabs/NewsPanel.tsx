import { cn } from "../utils/cn";

export type PanelState = "loading" | "error" | "empty" | "data";

interface NewsPanelProps {
  state: PanelState;
  error?: string | null;
  statusCode?: number;
  endpoint: string;
  items: unknown[];
  onRetry?: () => void;
}

function messageForState(
  state: PanelState,
  statusCode?: number,
  error?: string | null,
  endpoint?: string
): string {
  if (state === "loading") return "Loading…";
  if (state === "error") {
    if (statusCode === 404) return `Not deployed yet (${endpoint ?? "endpoint"})`;
    if (statusCode && statusCode >= 500) return `Server error (${statusCode})`;
    if (error?.toLowerCase().includes("timed out")) return "Request timed out";
    return error?.slice(0, 100) ?? "Request failed";
  }
  if (state === "empty") return "No news items yet";
  return "";
}

function countdownFromTimestamp(ts: unknown): string | null {
  if (ts == null) return null;
  const t = typeof ts === "number" ? ts : new Date(String(ts)).getTime();
  if (Number.isNaN(t)) return null;
  const diff = t - Date.now();
  if (diff <= 0) return "Past";
  const mins = Math.floor(diff / 60000);
  const hours = Math.floor(mins / 60);
  if (hours > 24) return `${Math.floor(hours / 24)}d`;
  if (hours > 0) return `${hours}h ${mins % 60}m`;
  return `${mins}m`;
}

export function NewsPanel({
  state,
  error,
  statusCode,
  endpoint,
  items,
  onRetry,
}: NewsPanelProps) {
  const hint = messageForState(state, statusCode, error, endpoint);
  const list = Array.isArray(items) ? items : [];

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      <div className="px-4 py-3 border-b border-slate-800 flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-white">News</h2>
          <p className="text-xs text-slate-500">
            {state === "data" ? `${list.length} item${list.length !== 1 ? "s" : ""}` : "—"}
          </p>
        </div>
      </div>

      <div id="news-list" className="flex-1 overflow-auto p-4">
        {state === "loading" && (
          <div className="flex items-center justify-center py-12">
            <div className="w-8 h-8 border-2 border-alpha-blue border-t-transparent rounded-full animate-spin" />
            <span className="ml-3 text-sm text-slate-400">Loading news…</span>
          </div>
        )}

        {state === "error" && (
          <div className="rounded-lg border border-alpha-amber/30 bg-alpha-amber/10 p-4">
            <p className="text-sm font-medium text-alpha-amber mb-1">Backend unavailable</p>
            <p className="text-xs text-slate-300 mb-3">{hint}</p>
            {onRetry && (
              <button
                type="button"
                onClick={onRetry}
                className="px-3 py-1.5 rounded text-xs font-medium bg-slate-700 text-slate-200 hover:bg-slate-600"
              >
                Retry
              </button>
            )}
          </div>
        )}

        {state === "empty" && (
          <div className="text-center py-12">
            <p className="text-slate-400 text-sm">No news items yet.</p>
            <p className="text-slate-500 text-xs mt-1">Endpoint: {endpoint}</p>
          </div>
        )}

        {state === "data" && list.length > 0 && (
          <div className="space-y-3">
            {list.slice(0, 30).map((item, i) => {
              const row = item as Record<string, unknown>;
              const title = String(row?.title ?? row?.headline ?? "—");
              const summary = row?.summary ?? row?.description;
              const ts = row?.ts_utc ?? row?.published_at ?? row?.timestamp ?? row?.date;
              const countdown = countdownFromTimestamp(ts);
              return (
                <div key={i} className="bg-slate-800/50 rounded-lg p-3 border border-slate-700/50">
                  <div className="flex items-start justify-between gap-2">
                    <h4 className="text-sm font-medium text-white flex-1">{title}</h4>
                    {countdown != null && (
                      <span className="text-xs text-slate-500 font-mono shrink-0">{countdown}</span>
                    )}
                  </div>
                  {summary != null && (
                    <p className="text-xs text-slate-400 mt-1 line-clamp-2">{String(summary)}</p>
                  )}
                </div>
              );
            })}
            {list.length > 30 && <p className="text-xs text-slate-500 pt-2">Showing first 30 of {list.length}</p>}
          </div>
        )}

        {state === "data" && list.length === 0 && (
          <div className="text-center py-12">
            <p className="text-slate-400 text-sm">No news items.</p>
            <p className="text-slate-500 text-xs mt-1">Countdown unavailable when no items</p>
          </div>
        )}
      </div>
    </div>
  );
}
