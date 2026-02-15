import { cn } from "../utils/cn";

export type PanelState = "loading" | "error" | "empty" | "data";

interface SignalsPanelProps {
  state: PanelState;
  error?: string | null;
  statusCode?: number;
  endpoint: string;
  signals: unknown[];
  filters: { instrument: string; strategy: string; confidence: number };
  selectedSignalId?: string | null;
  onSelectSignal?: (signal: unknown) => void;
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
  if (state === "empty") return "No signals yet";
  return "";
}

export function SignalsPanel({
  state,
  error,
  statusCode,
  endpoint,
  signals,
  filters,
  selectedSignalId,
  onSelectSignal,
  onRetry,
}: SignalsPanelProps) {
  const hint = messageForState(state, statusCode, error, endpoint);
  const list = Array.isArray(signals) ? signals : [];

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      <div className="px-4 py-3 border-b border-slate-800 flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-white">Active Signals</h2>
          <p className="text-xs text-slate-500">
            {state === "data" ? `${list.length} signal${list.length !== 1 ? "s" : ""}` : "—"}
          </p>
        </div>
      </div>

      <div id="signals-list" className="flex-1 overflow-auto p-4">
        {state === "loading" && (
          <div className="flex items-center justify-center py-12">
            <div className="w-8 h-8 border-2 border-alpha-blue border-t-transparent rounded-full animate-spin" />
            <span className="ml-3 text-sm text-slate-400">Loading signals…</span>
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
            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-slate-800/50 flex items-center justify-center">
              <svg className="w-8 h-8 text-slate-600" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
              </svg>
            </div>
            <p className="text-slate-400 text-sm font-medium mb-1">No signals yet</p>
            <p className="text-slate-500 text-xs">Endpoint: {endpoint}</p>
          </div>
        )}

        {state === "data" && list.length > 0 && (
          <div className="space-y-3">
            <div className="grid gap-3">
              {list.slice(0, 50).map((s, i) => {
                const row = s as Record<string, unknown>;
                const id = String(row?.id ?? row?.signal_id ?? i);
                const instrument = String(row?.instrument ?? row?.symbol ?? row?.pair ?? "—");
                const direction = String(row?.direction ?? row?.side ?? "—").toUpperCase();
                const strategy = String(row?.strategy ?? row?.strategy_key ?? "—");
                const confidence = row?.confidence ?? row?.score;
                const status = String(row?.status ?? "—");
                const isSelected = id === selectedSignalId;
                return (
                  <div
                    key={id}
                    onClick={() => onSelectSignal?.(row)}
                    className={cn(
                      "p-4 rounded-lg border cursor-pointer transition-all",
                      isSelected 
                        ? "bg-alpha-blue/20 border-alpha-blue ring-1 ring-alpha-blue shadow-lg shadow-alpha-blue/10" 
                        : status === "CONFIRMED" || status === "confirmed"
                          ? "bg-alpha-green/10 border-alpha-green/30 hover:bg-alpha-green/20"
                          : "bg-slate-800/50 border-slate-700/50 hover:bg-slate-800 hover:border-slate-600"
                    )}
                  >
                    <div className="flex items-start justify-between">
                      <div>
                        <span className="text-sm font-semibold text-white">{instrument}</span>
                        <span
                          className={cn(
                            "ml-2 px-2 py-0.5 rounded text-xs font-medium",
                            String(direction).startsWith("L") ? "bg-alpha-green/20 text-alpha-green" : "bg-alpha-red/20 text-alpha-red"
                          )}
                        >
                          {direction}
                        </span>
                      </div>
                      <span className="text-xs text-slate-400">{status}</span>
                    </div>
                    <div className="mt-2 flex items-center gap-3 text-xs text-slate-400">
                      <span>{strategy}</span>
                      {confidence != null && <span className="font-mono">{String(confidence)}%</span>}
                    </div>
                  </div>
                );
              })}
            </div>
            {list.length > 50 && (
              <p className="text-xs text-slate-500 pt-2">Showing first 50 of {list.length}</p>
            )}
          </div>
        )}

        {state === "data" && list.length === 0 && (
          <div className="text-center py-12">
            <p className="text-slate-400 text-sm">No signals match the current filters.</p>
            <p className="text-slate-500 text-xs mt-1">Instrument: {filters.instrument} · Strategy: {filters.strategy}</p>
          </div>
        )}
      </div>
    </div>
  );
}
