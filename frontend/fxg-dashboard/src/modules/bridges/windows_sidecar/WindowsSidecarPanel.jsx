import React, { useState, useEffect } from 'react';
import BridgeStatusCard from '../shared/BridgeStatusCard';
import { BRIDGE_IDS } from '../shared/models';

const SIDECAR_BASE = '/api/mt5_sidecar';

/**
 * WindowsSidecarPanel - Parallel Windows Sidecar bridge (read-only MT5 API).
 * Data/Diagnostics only. Execution = canonical_mac_file_bridge_v1.
 * No trades sent by sidecar. If MT5_SIDECAR_BASE_URL unset, treat as sidecar_unreachable.
 */
export default function WindowsSidecarPanel() {
  const [status, setStatus] = useState(null);
  const [tick, setTick] = useState(null);
  const [target, setTarget] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchTarget = async () => {
      try {
        const r = await fetch('/api/sidecar_target');
        setTarget(await r.json());
      } catch { setTarget({ target_kind: 'unset' }); }
    };
    fetchTarget();
    const t = setInterval(fetchTarget, 30000);
    return () => clearInterval(t);
  }, []);

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const r = await fetch(`${SIDECAR_BASE}/health`);
        const data = await r.json();
        setStatus(data);
      } catch (e) {
        setStatus({ unreachable: true, failure_bucket: 'sidecar_unreachable', recommended_fix: e?.message || 'Network error' });
      }
      setLoading(false);
    };
    fetchStatus();
    const t = setInterval(fetchStatus, 10000);
    return () => clearInterval(t);
  }, []);

  useEffect(() => {
    if (status?.unreachable) return;
    const fetchTick = async () => {
      try {
        const r = await fetch(`${SIDECAR_BASE}/symbols/EURUSD/tick`);
        setTick(await r.json());
      } catch {
        setTick({ symbol: 'EURUSD', failure_bucket: 'sidecar_unreachable' });
      }
    };
    fetchTick();
    const t = setInterval(fetchTick, 15000);
    return () => clearInterval(t);
  }, [status?.unreachable]);

  if (loading) return <div className="text-sm text-slate-500">Loading Windows Sidecar...</div>;

  const healthy = status?.service_up && status?.account_connected && !status?.unreachable;
  const degraded = status?.service_up && !status?.account_connected && !status?.unreachable;

  return (
    <BridgeStatusCard
      title="Windows Sidecar Bridge"
      bridgeId={BRIDGE_IDS.WINDOWS_SIDECAR}
      healthy={healthy}
      degraded={degraded}
      failureBucket={status?.failure_bucket}
      recommendedFix={status?.recommended_fix}
      lastUpdateAgeMs={null}
    >
      <div className="space-y-2 text-sm">
        <p className="text-xs font-semibold text-slate-600 border-b border-slate-200 pb-1">Data/Diagnostics only · Execution = canonical bridge</p>
        <p className="text-xs text-amber-700 bg-amber-50 px-1 py-0.5 rounded">No trades sent by sidecar</p>
        {target && (
          <p className="text-xs text-slate-500">
            Target: <span className="font-mono">{target.target_kind || 'unset'}</span>
            {target.target_kind === 'remote_overlay' && <span className="text-emerald-600 ml-1">(overlay)</span>}
            {target.target_kind === 'home_lan' && <span className="text-blue-600 ml-1">(LAN)</span>}
          </p>
        )}
        {status?.unreachable ? (
          <p className="text-amber-600 text-xs">Sidecar unreachable. Set MT5_SIDECAR_BASE_URL on Control Plane server.</p>
        ) : (
          <>
            <div className="flex justify-between">
              <span>Terminal</span>
              <span className={status?.terminal_connected ? 'text-emerald-600' : 'text-amber-600'}>
                {status?.terminal_connected ? 'Connected' : 'Not connected'}
              </span>
            </div>
            <div className="flex justify-between">
              <span>Account</span>
              <span className={status?.account_connected ? 'text-emerald-600' : 'text-amber-600'}>
                {status?.account_connected ? 'Logged in' : 'Not logged in'}
              </span>
            </div>
            {tick && (
              <div className="mt-2 pt-2 border-t border-slate-100">
                <div className="text-xs font-medium text-slate-600 mb-1">
                  Symbol probe: {tick.symbol || 'EURUSD'}
                  {tick.broker_symbol_actual && (
                    <span className="ml-1 text-amber-700">(broker: {tick.broker_symbol_actual})</span>
                  )}
                </div>
                {tick.failure_bucket ? (
                  <div className="text-xs text-amber-600">
                    <span className="font-medium">{tick.failure_bucket}</span>
                    {tick.recommended_fix && <span className="block text-slate-500 mt-0.5">{tick.recommended_fix}</span>}
                    {tick.broker_symbol_actual && tick.failure_bucket === 'symbol_name_mismatch' && (
                      <span className="block text-emerald-600 mt-0.5">Use /symbols/{tick.broker_symbol_actual}/tick</span>
                    )}
                  </div>
                ) : (
                  <div className="flex justify-between text-xs">
                    <span>Bid {tick.bid}</span>
                    <span>Ask {tick.ask}</span>
                  </div>
                )}
              </div>
            )}
            <p className="text-xs text-slate-500 italic">Read-only. Account/positions/diagnostics.</p>
          </>
        )}
      </div>
    </BridgeStatusCard>
  );
}
