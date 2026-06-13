import React from 'react';

/**
 * BridgeComparisonTable - Shows both bridges distinctly.
 * Active data source, active execution source, lane focus.
 */
export default function BridgeComparisonTable({ canonicalStatus, sidecarStatus = null }) {
  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
      <div className="px-6 py-4 border-b border-slate-100 bg-slate-50/50">
        <h2 className="text-base font-bold text-slate-800">Bridge Estate Comparison</h2>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-200 bg-slate-50">
              <th className="px-4 py-3 text-left font-semibold text-slate-700">Function</th>
              <th className="px-4 py-3 text-left font-semibold text-slate-700">Canonical (Mac File)</th>
              <th className="px-4 py-3 text-left font-semibold text-slate-700">Windows Sidecar</th>
            </tr>
          </thead>
          <tbody>
            <tr className="border-b border-slate-100">
              <td className="px-4 py-3 font-medium">Execution (lane 010)</td>
              <td className="px-4 py-3 text-emerald-600">Owner</td>
              <td className="px-4 py-3 text-slate-400">—</td>
            </tr>
            <tr className="border-b border-slate-100">
              <td className="px-4 py-3 font-medium">Account/positions read</td>
              <td className="px-4 py-3 text-slate-400">—</td>
              <td className="px-4 py-3 text-emerald-600">{sidecarStatus?.healthy ? 'Owner' : 'Unreachable'}</td>
            </tr>
            <tr>
              <td className="px-4 py-3 font-medium">Bridge ID</td>
              <td className="px-4 py-3 font-mono text-xs">canonical_mac_file_bridge_v1</td>
              <td className="px-4 py-3 font-mono text-xs">parallel_windows_sidecar_bridge_v1</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}
