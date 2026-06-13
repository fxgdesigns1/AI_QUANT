import React from 'react';

/**
 * BridgeFailureBucketPanel - Explains failure buckets per bridge family.
 */
export default function BridgeFailureBucketPanel() {
  const canonicalBuckets = ['producer_fail', 'transport_fail', 'consumer_path_fail', 'ea_parse_fail', 'broker_reject_fail', 'unknown_fail'];
  const sidecarBuckets = ['sidecar_unreachable', 'terminal_not_running', 'mt5_initialize_failed', 'account_not_logged_in', 'account_info_unavailable', 'symbol_not_selected', 'symbol_not_found', 'symbol_name_mismatch', 'no_tick_data', 'tick_stale', 'history_unavailable', 'write_guard_blocked', 'broker_reject', 'unknown_fail'];
  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
      <div className="px-6 py-4 border-b border-slate-100 bg-slate-50/50">
        <h2 className="text-base font-bold text-slate-800">Bridge Failure Buckets</h2>
      </div>
      <div className="p-6 grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
          <h3 className="text-sm font-semibold text-slate-700 mb-2">Canonical (canonical_mac_file_bridge_v1)</h3>
          <ul className="text-xs text-slate-600 space-y-1 font-mono">
            {canonicalBuckets.map(b => <li key={b}>{b}</li>)}
          </ul>
        </div>
        <div>
          <h3 className="text-sm font-semibold text-slate-700 mb-2">Windows Sidecar (parallel_windows_sidecar_bridge_v1)</h3>
          <ul className="text-xs text-slate-600 space-y-1 font-mono">
            {sidecarBuckets.map(b => <li key={b}>{b}</li>)}
          </ul>
        </div>
      </div>
    </div>
  );
}
