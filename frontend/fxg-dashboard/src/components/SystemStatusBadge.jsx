import React, { useEffect, useState } from 'react';
import { getJSON } from '../api/client';

export default function SystemStatusBadge() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [warnings, setWarnings] = useState([]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await getJSON('/api/status');
        
        if (!res.ok) {
          if (!cancelled) {
            setData(null);
            setError(res.error || 'request_failed');
          }
          return;
        }

        const json = res.data;
        // Check TruthEnvelope
        const truth = json?.truth || null;
        const truthWarnings = Array.isArray(truth?.warnings) ? truth.warnings : [];
        
        if (!cancelled) setWarnings(truthWarnings);

        const body = (json && truth && truth.complete === true && json.data) ? json.data : null;
        
        if (!cancelled) {
          if (body) {
            setData(body);
            setError(null);
          } else {
            setData(null);
            setError(json?.error || 'NO BACKEND FACT AVAILABLE');
          }
        }
      } catch (e) {
        if (!cancelled) {
          setData(null);
          setError(e?.message || 'request_failed');
        }
      }
    })();
    return () => { cancelled = true; };
  }, []);

  if (!data) {
    return (
      <div className="px-3 py-2 rounded-md text-sm border border-rose-600 bg-rose-950 text-rose-100">
        <strong>NO BACKEND FACT AVAILABLE</strong>
        <span className="ml-2 opacity-80">/api/status: {String(error || 'missing')}</span>
        {warnings.length > 0 && (
          <div className="mt-2 text-[11px] text-amber-200 font-mono">
            warnings: {warnings.map((w) => String(w)).join(' | ')}
          </div>
        )}
      </div>
    );
  }

  const alive = data.execution_enabled;
  const reason = data.weekend_indicator
    ? 'Weekend'
    : data.no_trade_reason || 'See /api/system/why_no_trades';

  return (
    <div className="px-3 py-2 rounded-md text-sm border border-slate-600 bg-slate-900 text-slate-100">
      <strong>{alive ? 'SYSTEM ALIVE' : 'SYSTEM PAUSED'}</strong>
      <span className="ml-2 opacity-80">No trades because: {reason}</span>
    </div>
  );
}
