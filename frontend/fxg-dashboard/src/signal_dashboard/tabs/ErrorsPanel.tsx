import { cn } from "../utils/cn";
import type { ErrorData } from "../types";

export type PanelState = "loading" | "error" | "empty" | "data";

interface ErrorsPanelProps {
  state: PanelState;
  error?: string | null;
  statusCode?: number;
  data: ErrorData | null;
  onRetry?: () => void;
}

export function ErrorsPanel({
  state,
  error,
  statusCode,
  data,
  onRetry,
}: ErrorsPanelProps) {
  const events = data?.latest_events || [];

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      <div className="px-4 py-3 border-b border-slate-800 flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-white">System Health & Errors</h2>
          <p className="text-xs text-slate-500">
            Observability status: {data?.overall_status || "UNKNOWN"}
          </p>
        </div>
        {data?.top_blocker && (
          <div className="bg-rose-950/50 border border-rose-900 text-rose-300 text-xs px-3 py-1.5 rounded flex items-center gap-2">
            <span className="font-bold">BLOCKER:</span> {data.top_blocker}
          </div>
        )}
      </div>

      <div className="flex-1 overflow-auto p-4">
        {state === "loading" && (
          <div className="flex items-center justify-center py-12">
            <div className="w-8 h-8 border-2 border-alpha-blue border-t-transparent rounded-full animate-spin" />
            <span className="ml-3 text-sm text-slate-400">Loading observability data…</span>
          </div>
        )}

        {state === "error" && (
          <div className="rounded-lg border border-alpha-amber/30 bg-alpha-amber/10 p-4">
            <p className="text-sm font-medium text-alpha-amber mb-1">Backend unavailable</p>
            <p className="text-xs text-slate-300 mb-3">{error}</p>
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

        {state === "data" && events.length === 0 && (
          <div className="text-center py-12">
            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-alpha-green/10 flex items-center justify-center">
              <svg className="w-8 h-8 text-alpha-green" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                <path d="M22 4L12 14.01l-3-3" />
              </svg>
            </div>
            <p className="text-slate-400 text-sm font-medium mb-1">All Systems Nominal</p>
            <p className="text-slate-500 text-xs">No recent error events recorded.</p>
          </div>
        )}

        {state === "data" && events.length > 0 && (
          <div className="space-y-3">
            {events.map((evt, i) => (
              <div
                key={i}
                className={cn(
                  "p-3 rounded-lg border text-sm",
                  evt.severity === "ERROR" || evt.severity === "CRITICAL"
                    ? "bg-rose-950/20 border-rose-900 text-rose-200"
                    : evt.severity === "WARNING"
                      ? "bg-amber-950/20 border-amber-900 text-amber-200"
                      : "bg-slate-800/50 border-slate-700 text-slate-300"
                )}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="font-bold text-xs uppercase opacity-80">{evt.severity}</span>
                  <span className="font-mono text-[10px] opacity-60">
                    {evt.ts ? new Date(evt.ts).toLocaleTimeString() : "—"}
                  </span>
                </div>
                <p className="mb-2 font-medium">{evt.message}</p>
                {evt.hint_cmd && (
                  <div className="bg-black/30 p-2 rounded font-mono text-xs text-slate-400 select-all">
                    {evt.hint_cmd}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
