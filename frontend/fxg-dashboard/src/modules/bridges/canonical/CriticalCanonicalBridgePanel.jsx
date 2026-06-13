import React from 'react';
import BridgeStatusCard from '../shared/BridgeStatusCard';
import { BRIDGE_IDS } from '../shared/models';

/**
 * CriticalCanonicalBridgePanel - Canonical ALPHA -> Mac Sync -> MT5 execution bridge.
 * DO NOT modify. Shows canonical bridge health only.
 */
export default function CriticalCanonicalBridgePanel({ bridgeStatus }) {
  const running = bridgeStatus?.running ?? false;
  const healthy = running;
  const degraded = bridgeStatus?.service_status === 'inactive';
  return (
    <BridgeStatusCard
      title="Canonical Bridge (ALPHA → Mac Sync → MT5)"
      bridgeId={BRIDGE_IDS.CANONICAL}
      healthy={healthy}
      degraded={degraded}
      failureBucket={null}
      recommendedFix={!running ? 'Check systemd ai-quant-bridge.service or process list' : null}
      lastUpdateAgeMs={null}
    >
      <div className="space-y-2 text-sm">
        <div className="flex justify-between">
          <span>Status</span>
          <span className={healthy ? 'text-emerald-600' : 'text-amber-600'}>
            {bridgeStatus?.running ? 'CONNECTED' : bridgeStatus?.service_status === 'inactive' ? 'IDLE' : 'NOT RUNNING'}
          </span>
        </div>
        {bridgeStatus?.last_heartbeat && (
          <div className="text-xs text-slate-500">Last heartbeat: {new Date(bridgeStatus.last_heartbeat).toLocaleString()}</div>
        )}
        <p className="text-xs font-semibold text-slate-600">Execution owner · Test trades must use canonical bridge, not sidecar</p>
        <p className="text-xs text-slate-500 italic">Locked canonical. Execution signal bridge for lane 010.</p>
      </div>
    </BridgeStatusCard>
  );
}
