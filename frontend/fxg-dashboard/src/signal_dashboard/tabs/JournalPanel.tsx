import { cn } from "../utils/cn";

export type PanelState = "loading" | "error" | "empty" | "data";

interface JournalPanelProps {
  state: PanelState;
  error?: string | null;
  statusCode?: number;
  endpoint: string;
  trades: unknown[];
  total?: number;
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
  if (state === "empty") return "No trades yet";
  return "";
}

function formatDate(iso: unknown): string {
  if (iso == null) return "—";
  const d = new Date(String(iso));
  if (Number.isNaN(d.getTime())) return String(iso);
  return d.toLocaleDateString("en-GB", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
}

export function JournalPanel({
  state,
  error,
  statusCode,
  endpoint,
  trades,
  total = 0,
  onRetry,
}: JournalPanelProps) {
  const hint = messageForState(state, statusCode, error, endpoint);
  const list = Array.isArray(trades) ? trades : [];

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      <div className="px-4 py-3 border-b border-slate-800 flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-white">Trade Journal</h2>
          <p className="text-xs text-slate-500">
            {state === "data" ? `${list.length} shown${total > 0 ? ` of ${total}` : ""}` : "—"}
          </p>
        </div>
      </div>

      <div id="journal-list" className="flex-1 overflow-auto p-4">
        {state === "loading" && (
          <div className="flex items-center justify-center py-12">
            <div className="w-8 h-8 border-2 border-alpha-blue border-t-transparent rounded-full animate-spin" />
            <span className="ml-3 text-sm text-slate-400">Loading journal…</span>
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
                <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
                <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
              </svg>
            </div>
            <p className="text-slate-400 text-sm font-medium mb-1">No trades yet</p>
            <p className="text-slate-500 text-xs">Endpoint: {endpoint}</p>
          </div>
        )}

        {state === "data" && list.length > 0 && (
          <div className="rounded-lg border border-slate-700/50 overflow-hidden">
            <table className="w-full text-xs">
              <thead className="bg-slate-900/50">
                <tr className="text-left text-slate-500">
                  <th className="px-4 py-2 font-medium">Time</th>
                  <th className="px-4 py-2 font-medium">Instrument</th>
                  <th className="px-4 py-2 font-medium">Strategy</th>
                  <th className="px-4 py-2 font-medium">Dir</th>
                  <th className="px-4 py-2 font-medium text-right">PnL</th>
                </tr>
              </thead>
              <tbody>
                {list.slice(0, 100).map((t, i) => {
                  const row = t as Record<string, unknown>;
                  const entryTime = row?.entry_time ?? row?.entryTime ?? row?.open_time;
                  const instrument = String(row?.instrument ?? row?.symbol ?? row?.pair ?? "—");
                  const strategy = String(row?.strategy ?? row?.strategy_key ?? "—");
                  const direction = String(row?.direction ?? row?.side ?? "—").toUpperCase();
                  const pnl = row?.pnl ?? row?.profit ?? row?.pl;
                  const pnlNum = typeof pnl === "number" ? pnl : Number(pnl);
                  return (
                    <tr key={i} className="border-t border-slate-800/50 hover:bg-slate-800/30">
                      <td className="px-4 py-2 text-slate-400 font-mono">{formatDate(entryTime)}</td>
                      <td className="px-4 py-2 text-slate-200 font-medium">{instrument}</td>
                      <td className="px-4 py-2 text-slate-400">{strategy.replace(/_/g, " ")}</td>
                      <td className="px-4 py-2 text-slate-400">{direction}</td>
                      <td className={cn("px-4 py-2 text-right font-mono", pnlNum >= 0 ? "text-alpha-green" : "text-alpha-red")}>
                        {pnl != null ? pnlNum : "—"}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            {list.length > 100 && (
              <div className="px-4 py-2 bg-slate-800/30 text-slate-500 text-xs">Showing first 100 of {list.length}</div>
            )}
          </div>
        )}

        {state === "data" && list.length === 0 && (
          <div className="text-center py-12">
            <p className="text-slate-400 text-sm">No trades in journal.</p>
            <p className="text-slate-500 text-xs mt-1">Last refresh: now</p>
          </div>
        )}
      </div>
    </div>
  );
}
