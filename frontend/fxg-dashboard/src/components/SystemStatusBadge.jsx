import React, { useEffect, useState } from 'react';

export default function SystemStatusBadge() {
  const [data, setData] = useState(null);
  useEffect(() => {
    fetch('/api/status')
      .then((r) => r.json())
      .then((j) => setData(j?.data || null))
      .catch(() => setData(null));
  }, []);

  if (!data) return null;

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
