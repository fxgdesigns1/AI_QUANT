import { cn } from "../utils/cn";
import type { SystemHealth } from "../types";

interface TopBarProps {
  health: SystemHealth;
  newsCount?: number;
}

export function TopBar({ health, newsCount }: TopBarProps) {
  const statusColors: Record<string, string> = {
    RUNNING: "bg-alpha-green",
    STOPPED: "bg-alpha-amber",
    ERROR: "bg-alpha-red",
    UNKNOWN: "bg-slate-500",
  };

  const formatTime = (iso: string | null) => {
    if (!iso) return "n/a";
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return "n/a";
    return d.toLocaleTimeString("en-GB", {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      timeZoneName: "short",
    });
  };

  const lockText =
    health.safetyLock === "LOCKED"
      ? "LOCKED"
      : health.safetyLock === "UNLOCKED"
        ? "UNLOCKED"
        : "UNKNOWN";

  const reason = health.weekend ? "WEEKEND" : (health.noTradeReason || null);

  return (
    <header className="bg-slate-925 border-b border-slate-800 px-4 py-2.5">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-gradient-to-br from-alpha-cyan to-alpha-blue rounded-lg flex items-center justify-center">
              <svg className="w-5 h-5 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                <path d="M3 3v18h18" strokeLinecap="round" strokeLinejoin="round" />
                <path d="M18 9l-5-6-4 8-3-2" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </div>
            <div>
              <h1 className="text-sm font-semibold text-white tracking-tight">FXG ALPHA</h1>
              <span className="text-[10px] text-slate-500 font-mono">{health.version ? `v${health.version}` : "v?"}</span>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <div className="px-2.5 py-1 bg-alpha-blue/20 border border-alpha-blue/30 rounded text-alpha-blue text-xs font-medium">
              {health.mode ?? "MODE: n/a"}
            </div>
            {reason && (
              <div className="px-2.5 py-1 bg-alpha-amber/20 border border-alpha-amber/30 rounded text-alpha-amber text-xs font-medium animate-pulse">
                {reason}
              </div>
            )}
          </div>
        </div>

        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2">
            <div
              className={cn(
                "w-2 h-2 rounded-full",
                statusColors[health.status] ?? "bg-slate-500",
                health.status === "RUNNING" && "signal-pulse"
              )}
            />
            <span className="text-xs text-slate-400">Service</span>
            <span
              className={cn(
                "text-xs font-medium",
                health.status === "RUNNING"
                  ? "text-alpha-green"
                  : health.status === "ERROR"
                    ? "text-alpha-red"
                    : health.status === "STOPPED"
                      ? "text-alpha-amber"
                      : "text-slate-300"
              )}
            >
              {health.status}
            </span>
          </div>

          <div className="flex items-center gap-2">
            <svg className="w-3.5 h-3.5 text-slate-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
              <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
            </svg>
            <span className="text-xs text-slate-400">Heartbeat</span>
            <span className="text-xs font-mono text-slate-300">{formatTime(health.lastHeartbeat)}</span>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-400">News</span>
            <span id="news-count" className="text-xs font-mono text-slate-300">{newsCount ?? 0}</span>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div
            className={cn(
              "flex items-center gap-2 px-3 py-1.5 rounded border",
              lockText === "LOCKED"
                ? "bg-alpha-green/10 border-alpha-green/30"
                : lockText === "UNLOCKED"
                  ? "bg-alpha-red/10 border-alpha-red/30"
                  : "bg-slate-800/40 border-slate-700/60"
            )}
          >
            <div className="flex gap-0.5">
              {[1, 2, 3].map((i) => (
                <svg
                  key={i}
                  className={cn(
                    "w-3.5 h-3.5",
                    lockText === "LOCKED"
                      ? "text-alpha-green"
                      : lockText === "UNLOCKED"
                        ? "text-alpha-red"
                        : "text-slate-400"
                  )}
                  viewBox="0 0 24 24"
                  fill="currentColor"
                >
                  <path d="M12 2C9.24 2 7 4.24 7 7v3H6a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8a2 2 0 0 0-2-2h-1V7c0-2.76-2.24-5-5-5zm0 2c1.66 0 3 1.34 3 3v3H9V7c0-1.66 1.34-3 3-3z" />
                </svg>
              ))}
            </div>
            <span className={cn("text-xs font-medium", lockText === "UNKNOWN" ? "text-slate-300" : undefined)}>{lockText}</span>
          </div>
        </div>
      </div>
    </header>
  );
}
