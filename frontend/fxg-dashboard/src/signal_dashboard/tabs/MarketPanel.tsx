import { cn } from "../utils/cn";

export type PanelState = "loading" | "error" | "empty" | "data";

interface MarketPanelProps {
  state: PanelState;
  error?: string | null;
  statusCode?: number;
  endpoint: string;
  instruments: Array<{
    instrument: string;
    mid?: number;
    time?: string;
    regime?: {
      regime: string;
      adx?: number;
    };
  }>;
  ts_utc?: string;
  onRetry?: () => void;
}

export function MarketPanel({
  state,
  error,
  statusCode,
  endpoint,
  instruments,
  ts_utc,
  onRetry,
}: MarketPanelProps) {
  const list = instruments || [];

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      <div className="px-4 py-3 border-b border-slate-800 flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-white">Market Overview</h2>
          <p className="text-xs text-slate-500">
            Regime and pricing · Last updated: {ts_utc ? new Date(ts_utc).toLocaleTimeString() : '—'}
          </p>
        </div>
      </div>

      <div className="flex-1 overflow-auto p-4">
        {state === "loading" && (
          <div className="flex items-center justify-center py-12">
            <div className="w-8 h-8 border-2 border-alpha-blue border-t-transparent rounded-full animate-spin" />
            <span className="ml-3 text-sm text-slate-400">Loading market data…</span>
          </div>
        )}

        {state === "error" && (
          <div className="rounded-lg border border-alpha-amber/30 bg-alpha-amber/10 p-4">
            <p className="text-sm font-medium text-alpha-amber mb-1">Backend unavailable</p>
            <p className="text-xs text-slate-300 mb-3">{error || `Status: ${statusCode}`}</p>
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

        {state === "data" && (
          <div className="rounded-lg border border-slate-800 overflow-hidden">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-900 text-slate-400 font-medium border-b border-slate-800">
                <tr>
                  <th className="px-4 py-3">Instrument</th>
                  <th className="px-4 py-3 text-right">Mid Price</th>
                  <th className="px-4 py-3">Regime</th>
                  <th className="px-4 py-3 text-right">ADX</th>
                  <th className="px-4 py-3 text-right">Time</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/50 bg-slate-900/30">
                {list.length === 0 ? (
                   <tr>
                     <td colSpan={5} className="px-4 py-8 text-center text-slate-500">No instruments configured</td>
                   </tr>
                ) : (
                  list.map((inst) => (
                    <tr key={inst.instrument} className="hover:bg-slate-800/30">
                      <td className="px-4 py-3 font-medium text-slate-200">{inst.instrument}</td>
                      <td className="px-4 py-3 text-right font-mono text-slate-300">
                        {inst.mid?.toFixed(5) ?? "—"}
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className={cn(
                            "px-2 py-0.5 rounded text-xs font-medium uppercase",
                            inst.regime?.regime?.includes("TREND")
                              ? "bg-alpha-blue/20 text-alpha-blue"
                              : inst.regime?.regime?.includes("RANGE")
                                ? "bg-alpha-amber/20 text-alpha-amber"
                                : "bg-slate-700 text-slate-400"
                          )}
                        >
                          {inst.regime?.regime ?? "UNKNOWN"}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right font-mono text-slate-400">
                        {inst.regime?.adx?.toFixed(1) ?? "—"}
                      </td>
                      <td className="px-4 py-3 text-right text-xs text-slate-500 font-mono">
                        {inst.time ? new Date(inst.time).toLocaleTimeString() : "—"}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
