import React from 'react';

export default function ReadinessPanel({ instrument, data }) {
  if (!data) return null;

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden p-6 mb-4">
      <div className="flex justify-between items-center mb-4 border-b border-slate-100 pb-2">
        <h3 className="text-lg font-bold text-slate-800">{instrument}</h3>
        <div className={`px-3 py-1 rounded-full text-xs font-bold border ${
          data.status.includes('BLOCKED') ? 'bg-rose-100 text-rose-700 border-rose-200' :
          data.status.includes('WAITING') ? 'bg-amber-100 text-amber-700 border-amber-200' :
          'bg-emerald-100 text-emerald-700 border-emerald-200'
        }`}>
          {data.status}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
        <div className="space-y-2">
          <div className="flex justify-between">
            <span className="text-slate-500 font-semibold">READINESS:</span>
            <span className="font-mono font-bold">{data.readiness_score} / 100</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-500 font-semibold">WHY NOT TRADING:</span>
            <span className="font-mono text-slate-700 text-right">{data.why_not_trading}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-500 font-semibold">SESSION:</span>
            <span className={`font-mono font-bold ${data.session_state === 'OPEN' ? 'text-emerald-600' : 'text-slate-600'}`}>
              {data.session_state}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-500 font-semibold">SIGNALS:</span>
            <span className="font-mono text-slate-700">{data.signal_state}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-500 font-semibold">CONFIDENCE:</span>
            <span className="font-mono text-slate-700">{data.signal_confidence}</span>
          </div>
        </div>

        <div className="space-y-2">
          <div className="flex justify-between">
            <span className="text-slate-500 font-semibold">BIAS:</span>
            <span className="font-mono text-slate-700">{data.bias_state}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-500 font-semibold">REGIME:</span>
            <span className="font-mono text-slate-700">{data.regime}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-500 font-semibold">NEXT UNBLOCK:</span>
            <span className="font-mono text-slate-700 text-right">{data.nearest_unblock_event}</span>
          </div>
        </div>
      </div>

      <div className="mt-4 pt-4 border-t border-slate-100">
        <div className="text-xs text-slate-500 font-semibold uppercase mb-1">System Summary</div>
        <div className="text-sm text-slate-700 font-medium italic">
          {data.summary}
        </div>
      </div>
    </div>
  );
}
