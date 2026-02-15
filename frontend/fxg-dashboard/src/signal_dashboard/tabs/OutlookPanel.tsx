import { cn } from "../utils/cn";

export type PanelState = "loading" | "error" | "empty" | "data";

interface OutlookPanelProps {
  state: PanelState;
  error?: string | null;
  statusCode?: number;
  endpoint: string;
  outlook: Record<string, unknown> | null;
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
  if (state === "empty") return "No outlook data yet";
  return "";
}

export function OutlookPanel({
  state,
  error,
  statusCode,
  endpoint,
  outlook,
  onRetry,
}: OutlookPanelProps) {
  const hint = messageForState(state, statusCode, error, endpoint);
  const overall = outlook?.overall ?? outlook?.bias ?? outlook?.summary;
  const instruments = (outlook?.instruments ?? outlook?.pairs) as Record<string, { bias?: string; confidence?: number }> | undefined;
  const drivers = (outlook?.drivers ?? outlook?.key_drivers) as string[] | undefined;
  const shortTerm = outlook?.short_term_outlook ?? outlook?.shortTermOutlook ?? outlook?.summary;

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      <div className="px-4 py-3 border-b border-slate-800">
        <h2 className="text-lg font-semibold text-white">Market Outlook</h2>
        <p className="text-xs text-slate-500">Daily horizon · endpoint: {endpoint}</p>
      </div>

      <div className="flex-1 overflow-auto p-4 space-y-6">
        {state === "loading" && (
          <div className="flex items-center justify-center py-12">
            <div className="w-8 h-8 border-2 border-alpha-blue border-t-transparent rounded-full animate-spin" />
            <span className="ml-3 text-sm text-slate-400">Loading outlook…</span>
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

        {(state === "empty" || (state === "data" && !outlook)) && (
          <div className="text-center py-12">
            <p className="text-slate-400 text-sm">No outlook data yet.</p>
            <p className="text-slate-500 text-xs mt-1">Endpoint: {endpoint}</p>
          </div>
        )}

        {state === "data" && outlook && (
          <>
            {overall != null && (
              <div className={cn("p-4 rounded-xl border bg-slate-800/50 border-slate-700/50")}>
                <div className="text-xs text-slate-500 uppercase tracking-wider mb-1">Overall</div>
                <div className="text-xl font-bold text-white">{String(overall)}</div>
              </div>
            )}
            {instruments && Object.keys(instruments).length > 0 && (
              <div>
                <h3 className="text-sm font-medium text-slate-400 mb-3">Instruments</h3>
                <div className="grid grid-cols-2 gap-3">
                  {Object.entries(instruments).map(([inst, data]) => (
                    <div key={inst} className="bg-slate-800/50 rounded-lg p-3 border border-slate-700/50">
                      <span className="text-sm font-medium text-white">{inst}</span>
                      <span className="ml-2 text-xs text-slate-400">{data?.bias ?? "—"}</span>
                      {data?.confidence != null && (
                        <span className="ml-2 text-xs text-slate-500">{data.confidence}%</span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
            {drivers && drivers.length > 0 && (
              <div>
                <h3 className="text-sm font-medium text-slate-400 mb-3">Drivers</h3>
                <ul className="space-y-2">
                  {drivers.map((d, i) => (
                    <li key={i} className="text-sm text-slate-300 bg-slate-800/30 rounded-lg p-3">
                      {String(d)}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {shortTerm != null && (
              <div className="bg-slate-800/50 rounded-lg p-4 border border-slate-700/50">
                <h4 className="text-sm font-medium text-white mb-2">Short-term</h4>
                <p className="text-sm text-slate-400">{String(shortTerm)}</p>
              </div>
            )}
            {!overall && !instruments?.length && !drivers?.length && shortTerm == null && (
              <p className="text-slate-500 text-sm">Outlook payload has no displayable fields.</p>
            )}
          </>
        )}
      </div>
    </div>
  );
}
