import React, { useState, useEffect } from 'react';

/**
 * BridgeSwitchStatePanel - Current switch state: which bridge owns which function.
 */
export default function BridgeSwitchStatePanel() {
  const [target, setTarget] = useState(null);
  useEffect(() => {
    fetch('/api/sidecar_target').then(r => r.json()).then(setTarget).catch(() => setTarget({ target_kind: 'unset' }));
  }, []);

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
      <div className="px-6 py-4 border-b border-slate-100 bg-slate-50/50">
        <h2 className="text-base font-bold text-slate-800">Current Switch State</h2>
      </div>
      <div className="p-6 space-y-2 text-sm">
        <div className="flex justify-between">
          <span className="text-slate-600">Execution bridge</span>
          <span className="font-mono text-slate-800">canonical_mac_file_bridge_v1 (consumed by Windows MT5 EA)</span>
        </div>
        <div className="flex justify-between">
          <span className="text-slate-600">Data bridge (MT5 read)</span>
          <span className="font-mono text-slate-800">parallel_windows_sidecar_bridge_v1</span>
        </div>
        <div className="flex justify-between">
          <span className="text-slate-600">Diagnostics bridge</span>
          <span className="font-mono text-slate-800">parallel_windows_sidecar_bridge_v1</span>
        </div>
        <div className="flex justify-between">
          <span className="text-slate-600">Sidecar mode</span>
          <span className="font-mono text-slate-800">read_only_first</span>
        </div>
        <div className="flex justify-between">
          <span className="text-slate-600">Telemetry target</span>
          <span className="font-mono text-slate-800">{target?.target_kind || 'unset'}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-slate-600">Active lane focus</span>
          <span className="font-mono text-slate-800">010_manual</span>
        </div>
        <p className="text-xs text-amber-700 bg-amber-50 px-2 py-1 rounded mt-3">
          Do not rely on sleeping Windows PC for market execution. Keep trading PC awake during trading hours.
        </p>
        <p className="text-xs text-slate-500">No silent cutover. Operator chooses explicit cutover when ready.</p>
      </div>
    </div>
  );
}
