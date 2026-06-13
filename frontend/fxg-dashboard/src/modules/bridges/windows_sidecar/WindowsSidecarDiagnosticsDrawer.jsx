import React, { useState, useEffect } from 'react';

const SIDECAR_BASE = '/api/mt5_sidecar';

/**
 * WindowsSidecarDiagnosticsDrawer - Expandable diagnostics from sidecar /diagnostics.
 */
export default function WindowsSidecarDiagnosticsDrawer({ open, onClose }) {
  const [diag, setDiag] = useState(null);

  useEffect(() => {
    if (!open) return;
    fetch(`${SIDECAR_BASE}/diagnostics`)
      .then(r => r.json())
      .then(setDiag)
      .catch(() => setDiag({ error: 'Unreachable' }));
  }, [open]);

  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={onClose}>
      <div className="bg-white rounded-xl shadow-xl max-w-lg w-full mx-4 max-h-[80vh] overflow-auto p-6" onClick={e => e.stopPropagation()}>
        <h3 className="text-lg font-bold mb-4">Windows Sidecar Diagnostics</h3>
        {diag?.error ? (
          <p className="text-amber-600">{diag.error}</p>
        ) : diag ? (
          <pre className="text-xs font-mono bg-slate-50 p-4 rounded overflow-x-auto">
            {JSON.stringify(diag, null, 2)}
          </pre>
        ) : (
          <p>Loading...</p>
        )}
        <button onClick={onClose} className="mt-4 px-4 py-2 bg-slate-200 rounded hover:bg-slate-300">Close</button>
      </div>
    </div>
  );
}
