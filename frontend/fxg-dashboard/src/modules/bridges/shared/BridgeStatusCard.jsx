import React from 'react';
import { Radio, AlertTriangle, CheckCircle } from 'lucide-react';

/**
 * BridgeStatusCard - Displays status for a single bridge with explicit bridge_id.
 * Never use generic "MT5" label without estate id.
 */
export default function BridgeStatusCard({ title, bridgeId, healthy, degraded, failureBucket, recommendedFix, lastUpdateAgeMs, children }) {
  const variant = healthy ? 'success' : degraded ? 'warning' : 'danger';
  const Icon = healthy ? CheckCircle : degraded ? AlertTriangle : Radio;
  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
      <div className="px-6 py-4 border-b border-slate-100 bg-slate-50/50 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Icon className={`w-5 h-5 ${healthy ? 'text-emerald-500' : degraded ? 'text-amber-500' : 'text-slate-500'}`} />
          <h2 className="text-base font-bold text-slate-800">{title}</h2>
        </div>
        <span className="text-xs font-mono text-slate-500">{bridgeId}</span>
      </div>
      <div className="p-6 space-y-3">
        {failureBucket && (
          <div className="text-xs text-amber-700 bg-amber-50 p-2 rounded border border-amber-200">
            <span className="font-semibold">Failure bucket:</span> {failureBucket}
          </div>
        )}
        {recommendedFix && (
          <div className="text-xs text-slate-600 bg-slate-50 p-2 rounded border border-slate-200">
            <span className="font-semibold">Recommended fix:</span> {recommendedFix}
          </div>
        )}
        {lastUpdateAgeMs != null && (
          <div className="text-xs text-slate-500">Last update: {lastUpdateAgeMs}ms ago</div>
        )}
        {children}
      </div>
    </div>
  );
}
