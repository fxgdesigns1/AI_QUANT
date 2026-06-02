import { useEffect, useState } from "react";
import { getJSON } from "../../api/client";

interface LogEntry {
  ts: string;
  level: string;
  msg: string;
  [key: string]: unknown;
}

export function SystemLogs() {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchLogs = async () => {
    // try/catch handled inside getJSON but we need explicit error handling here too
    const r = await getJSON<{ logs: LogEntry[] }>("/api/logs/alpha?limit=50");
    setLoading(false);
    if (r.ok) {
      setLogs(r.data?.logs?.reverse() ?? []);
      setError(null);
    } else {
      setError("Unable to fetch logs");
    }
  };

  useEffect(() => {
    fetchLogs();
    const t = setInterval(fetchLogs, 10000);
    return () => clearInterval(t);
  }, []);

  return (
    <div className="flex-1 flex flex-col min-h-0 bg-slate-950 border-t border-slate-800">
      <div className="px-3 py-2 border-b border-slate-800 flex justify-between items-center bg-slate-900/50">
        <h3 className="text-[10px] font-medium text-slate-500 uppercase tracking-wider">System Logs</h3>
        <span className="text-[10px] text-slate-600 font-mono">/api/logs/alpha</span>
      </div>
      
      <div className="flex-1 overflow-y-auto p-2 space-y-1 font-mono text-[10px]">
        {loading && <div className="text-slate-500 italic px-1">Loading...</div>}
        
        {error && (
          <div className="text-red-400 px-1 py-0.5 bg-red-900/20 rounded">
            {error}
          </div>
        )}

        {!loading && !error && logs.length === 0 && (
          <div className="text-slate-600 italic px-1">No logs available.</div>
        )}

        {logs.map((log, i) => (
          <div key={i} className="flex gap-2 text-slate-400 border-b border-slate-800/50 pb-1 last:border-0">
            <span className="text-slate-500 shrink-0 w-14 truncate" title={log.ts}>{log.ts?.split('T')[1]?.split('.')[0] || "time"}</span>
            <span className={`shrink-0 w-8 font-bold ${
              log.level === 'ERROR' ? 'text-red-400' : 
              log.level === 'WARNING' ? 'text-amber-400' : 'text-blue-400'
            }`}>{log.level?.slice(0,4)}</span>
            <span className="text-slate-300 break-words">{log.msg}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
