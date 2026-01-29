export function mapReadinessData(backendData: any) {
  if (!backendData || !backendData.available || !backendData.instruments) {
    return {};
  }

  const result: any = {};

  Object.entries(backendData.instruments).forEach(([instrument, data]: [string, any]) => {
    const primary_blocker = data.primary_blocker;
    const readiness_score = data.readiness_score || 0;
    const why_not_trading = data.why_not_trading;
    const session_gate_result = data.session_gate_result;
    const signals_emitted = data.signals_emitted || 0;
    const strategies_evaluated = data.strategies_evaluated || 0;
    const signal_confidence = data.signal_confidence;
    const bias_state = data.bias_state || 'UNKNOWN';
    const regime = data.regime || 'UNKNOWN';
    const nearest_unblock_event = data.nearest_unblock_event || 'Unknown';

    // Status logic
    let status = 'READY';
    if (primary_blocker === 'SESSION_GATE') {
      status = 'BLOCKED — SESSION';
    } else if (primary_blocker === 'SIGNAL_ENGINE') {
      status = 'WAITING — SIGNAL';
    } else if (primary_blocker) {
      status = `BLOCKED — ${primary_blocker}`;
    }

    // Session state
    const session_state = session_gate_result === 'ALLOW' ? 'OPEN' : 'CLOSED';

    // Signal state
    let signal_state = 'NOT EVALUATED';
    if (signals_emitted > 0) {
      signal_state = 'SIGNAL READY';
    } else if (strategies_evaluated > 0) {
      signal_state = 'EVALUATED — NONE QUALIFY';
    }

    // Summary calculation
    let summary = '';
    if (status.startsWith('BLOCKED')) {
      summary = `System is blocked by ${primary_blocker}. Next unblock: ${nearest_unblock_event}`;
    } else if (status.startsWith('WAITING')) {
      summary = `System is ready and scanning. evaluated ${strategies_evaluated} strategies.`;
    } else {
      summary = `System is fully ready. Score: ${readiness_score}`;
    }

    result[instrument] = {
      status,
      readiness_score,
      why_not_trading: why_not_trading || primary_blocker || 'None',
      session_state,
      signal_state,
      signal_confidence: signal_confidence !== undefined ? signal_confidence : '—',
      bias_state,
      regime,
      nearest_unblock_event,
      summary
    };
  });

  return result;
}
