import React, { useState, useEffect, useCallback } from 'react';
import {
  Activity,
  Power,
  Radio,
  Terminal,
  Plus,
  Save,
  AlertTriangle,
  RefreshCw,
  Zap,
  ShieldAlert,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import '../styles/control-plane.css';
import ReadinessPanel from './ReadinessPanel';
import { mapReadinessData } from '../utils/readinessMapper';

const API_BASE = '/api';

// --- Reusable UI Components ---

const Card = ({ title, icon: Icon, children, className = '' }) => (
  <div className={`bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden ${className}`}>
    <div className="px-6 py-4 border-b border-slate-100 bg-slate-50/50 flex items-center gap-2">
      {Icon && <Icon className="w-5 h-5 text-slate-500" />}
      <h2 className="text-base font-bold text-slate-800">{title}</h2>
    </div>
    <div className="p-6">
      {children}
    </div>
  </div>
);

const Badge = ({ children, variant = 'neutral' }) => {
  const styles = {
    neutral: 'bg-slate-100 text-slate-600 border-slate-200',
    success: 'bg-emerald-100 text-emerald-700 border-emerald-200',
    warning: 'bg-amber-100 text-amber-700 border-amber-200',
    danger: 'bg-rose-100 text-rose-700 border-rose-200',
    info: 'bg-blue-100 text-blue-700 border-blue-200',
  };
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-bold border uppercase tracking-wide ${styles[variant]}`}>
      {children}
    </span>
  );
};

const LogPanel = ({ title, logs, emptyMessage }) => (
  <div className="bg-slate-900 rounded-lg overflow-hidden border border-slate-800 flex flex-col cp-log-panel">
    <div className="px-4 py-2.5 bg-slate-950 border-b border-slate-800 flex justify-between items-center shrink-0">
      <span className="text-xs font-mono text-slate-400 font-bold uppercase tracking-wide">{title}</span>
      <span className="text-[10px] text-slate-500 font-mono">{logs.length} entries</span>
    </div>
    <div className="flex-1 overflow-y-auto p-4 font-mono text-xs space-y-1 cp-log-panel">
      {logs.length === 0 && (
        <div className="h-full flex flex-col items-center justify-center text-slate-500 gap-2">
          <Terminal className="w-8 h-8 opacity-25" />
          <span>{emptyMessage}</span>
        </div>
      )}
      {logs.map((log, i) => (
        <div key={i} className="cp-log-entry flex gap-2 p-1 rounded break-all">
          <span className="text-slate-500 shrink-0 select-none">[{log.timestamp?.split('T')[1]?.split('.')[0] || '00:00:00'}]</span>
          <span className={log.level === 'ERROR' ? 'text-rose-400' : log.signal ? 'text-emerald-400' : 'text-slate-400'}>
            {log.strategy && <span className="text-blue-400 mr-2 font-bold">{log.strategy}</span>}
            {log.signal && <span className="bg-emerald-900/30 text-emerald-300 px-1 rounded mr-2">{log.signal} {log.symbol}</span>}
            {log.message || JSON.stringify(log)}
          </span>
        </div>
      ))}
    </div>
  </div>
);

export default function ControlPlaneDashboard() {
  const [controlState, setControlState] = useState(null);
  const [routingConfig, setRoutingConfig] = useState(null);
  const [alphaLogs, setAlphaLogs] = useState([]);
  const [bridgeLogs, setBridgeLogs] = useState([]);
  const [biasStates, setBiasStates] = useState([]);
  const [health, setHealth] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [expandedBias, setExpandedBias] = useState(new Set());
  const [toast, setToast] = useState(null);
  const [whyNoTrades, setWhyNoTrades] = useState(null);
  const [bridgeStatus, setBridgeStatus] = useState(null);
  const [systemStatus, setSystemStatus] = useState(null);
  const [signalThinking, setSignalThinking] = useState(null);
  const [gateProximity, setGateProximity] = useState(null);
  const [reasoningSnapshot, setReasoningSnapshot] = useState(null);
  const [readinessObservability, setReadinessObservability] = useState({});

  const [newOutput, setNewOutput] = useState({
    bridge_account: '',
    enabled: true,
    lot_multiplier: 1.0,
    max_daily_loss: 500,
    max_trades_per_day: 5
  });

  const [showAddOutput, setShowAddOutput] = useState(false);

  const showToast = useCallback((message, variant = 'success') => {
    setToast({ message, variant });
  }, []);

  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => setToast(null), 2800);
    return () => clearTimeout(t);
  }, [toast]);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 2000);
    return () => clearInterval(interval);
  }, []);

  const fetchData = async () => {
    try {
      const [
        stateRes,
        routingRes,
        healthRes,
        alphaRes,
        bridgeRes,
        biasRes,
        statusRes,
        whyNoTradesRes,
        bridgeStatusRes,
        signalThinkingRes,
        gateProximityRes,
        reasoningRes,
        observabilityRes,
      ] = await Promise.all([
        fetch(`${API_BASE}/control/state`),
        fetch(`${API_BASE}/control/routing`),
        fetch(`${API_BASE}/health`),
        fetch(`${API_BASE}/logs/alpha`),
        fetch(`${API_BASE}/logs/bridge`),
        fetch(`${API_BASE}/bias/state`),
        fetch(`${API_BASE}/status`).catch(() => null),
        fetch(`${API_BASE}/system/why_no_trades`).catch(() => null),
        fetch(`${API_BASE}/bridge/status`).catch(() => null),
        fetch(`${API_BASE}/system/signal_thinking`).catch(() => null),
        fetch(`${API_BASE}/system/gate_proximity`).catch(() => null),
        fetch(`${API_BASE}/system/reasoning`).catch(() => null),
        fetch(`${API_BASE}/observability/readiness`).catch(() => null),
      ]);

      setControlState(await stateRes.json());
      setRoutingConfig(await routingRes.json());
      setHealth(await healthRes.json());
      setAlphaLogs((await alphaRes.json()).logs || []);
      setBridgeLogs((await bridgeRes.json()).logs || []);
      const biasData = await biasRes.json();
      setBiasStates(biasData.bias_states || []);
      
      if (statusRes) {
        const statusData = await statusRes.json();
        setSystemStatus(statusData);
      }
      
      if (whyNoTradesRes) {
        const whyData = await whyNoTradesRes.json();
        setWhyNoTrades(whyData);
      }
      
      if (bridgeStatusRes) {
        const bridgeData = await bridgeStatusRes.json();
        setBridgeStatus(bridgeData);
      }

      if (signalThinkingRes) {
        const thinkingData = await signalThinkingRes.json();
        setSignalThinking(thinkingData);
      }
      
      if (gateProximityRes) {
        const gateData = await gateProximityRes.json();
        setGateProximity(gateData);
      }
      
      if (reasoningRes) {
        const reasoningData = await reasoningRes.json();
        if (reasoningData.ok && reasoningData.snapshot) {
          setReasoningSnapshot(reasoningData.snapshot);
        } else {
          setReasoningSnapshot(null);
        }
      }

      if (observabilityRes) {
        const obsData = await observabilityRes.json();
        if (obsData && obsData.data) {
          setReadinessObservability(mapReadinessData(obsData.data));
        }
      }
      
      setLastUpdated(new Date());
      setLoading(false);
      setError(null);
    } catch (err) {
      console.error(err);
      setError("Control Plane API Offline");
      setHealth({ status: 'offline' });
      setLoading(false);
    }
  };

  const toggleGlobalTrading = async () => {
    if (!controlState) return;
    const newState = { ...controlState, global_trading_enabled: !controlState.global_trading_enabled };
    await updateControlState(newState);
  };

  const setExecutionMode = async (mode) => {
    if (!controlState) return;
    const newState = { ...controlState, execution_mode: mode };
    await updateControlState(newState);
  };

  const updateControlState = async (newState) => {
    try {
      const res = await fetch(`${API_BASE}/control/state`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newState)
      });
      setControlState(await res.json());
      showToast('Control state saved', 'success');
    } catch (err) {
      setError(err.message);
      showToast('Failed to save control state', 'danger');
    }
  };

  const toggleOutput = async (index) => {
    if (!routingConfig) return;
    const newOutputs = [...routingConfig.outputs];
    newOutputs[index].enabled = !newOutputs[index].enabled;
    await updateRoutingConfig({ outputs: newOutputs });
  };

  const updateMultiplier = async (index, value) => {
    if (!routingConfig) return;
    const newOutputs = [...routingConfig.outputs];
    newOutputs[index].lot_multiplier = parseFloat(value);
    await updateRoutingConfig({ outputs: newOutputs });
  };

  const updateRoutingConfig = async (newConfig) => {
    try {
      const res = await fetch(`${API_BASE}/control/routing`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newConfig)
      });
      setRoutingConfig(await res.json());
    } catch (err) {
      setError(err.message);
      showToast('Failed to update routing', 'danger');
    }
  };

  const handleAddOutput = async () => {
    if (!newOutput.bridge_account) return;
    try {
      await fetch(`${API_BASE}/control/routing/output`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newOutput)
      });
      setShowAddOutput(false);
      fetchData();
      setNewOutput({
        bridge_account: '',
        enabled: true,
        lot_multiplier: 1.0,
        max_daily_loss: 500,
        max_trades_per_day: 5
      });
      showToast('Route added', 'success');
    } catch (err) {
      setError(err.message);
      showToast('Failed to add route', 'danger');
    }
  };

  const isOffline = health?.status !== 'ok';

  if (loading) return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center">
      <div className="flex flex-col items-center gap-4 text-slate-400">
        <RefreshCw className="w-8 h-8 animate-spin" />
        <span className="font-semibold">Connecting to Control Plane...</span>
      </div>
    </div>
  );

  return (
    <div className="cp-dashboard min-h-screen bg-slate-50 text-slate-800 font-sans pb-12">
      {/* Navbar */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-20 shadow-sm">
        <div className="max-w-7xl mx-auto px-6 py-4 flex justify-between items-center">
          <div className="flex items-center gap-3">
            <div className="bg-indigo-600 p-2 rounded-lg">
              <Activity className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-slate-900 leading-none">Alpha Control Plane</h1>
              <p className="text-xs text-slate-500 font-medium mt-1">Local-First MT5 Bridge Controller</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            {lastUpdated && <span className="text-xs text-slate-400 font-mono hidden md:block">Last Sync: {lastUpdated.toLocaleTimeString()}</span>}
            <Badge variant={controlState?.execution_mode === 'LIVE' ? 'warning' : 'info'}>
              <ShieldAlert className="w-3 h-3" />
              {controlState?.execution_mode === 'LIVE' ? 'LIVE' : 'DRY-RUN'}
            </Badge>
            <Badge variant={isOffline ? 'danger' : 'success'}>
              {isOffline ? <AlertTriangle className="w-3 h-3" /> : <Zap className="w-3 h-3" />}
              API: {health?.status || 'OFFLINE'}
            </Badge>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-6 space-y-6">

        {isOffline && (
          <div className="bg-rose-50 border border-rose-200 rounded-lg p-4 flex items-center gap-3 text-rose-700 shadow-sm">
            <AlertTriangle className="w-5 h-5 shrink-0" />
            <span className="font-bold">Connection Lost:</span>
            <span>Control Plane API is unreachable. Controls are disabled.</span>
          </div>
        )}

        {/* Global Controls + Routing */}
        <section className="grid grid-cols-1 lg:grid-cols-2 gap-6" aria-label="Global Controls and Routing">
          
          {/* Global Configuration */}
          <Card title="Global Configuration" icon={Power} className={isOffline ? 'opacity-60 grayscale pointer-events-none select-none' : ''}>
            <div className="space-y-5">
              {/* Master Switch */}
              <div className="flex items-center justify-between p-4 bg-slate-50 rounded-lg border border-slate-100">
                <div className="flex gap-4">
                  <div className={`p-3 rounded-full ${controlState?.global_trading_enabled ? 'bg-emerald-100' : 'bg-slate-200'}`}>
                    <Power className={`w-6 h-6 ${controlState?.global_trading_enabled ? 'text-emerald-600' : 'text-slate-400'}`} />
                  </div>
                  <div>
                    <h3 className="text-sm font-bold text-slate-900">Master Trading Switch</h3>
                    <p className="text-xs text-slate-500 mt-1 max-w-[200px]">
                      When disabled, all signal generation is halted immediately at the source.
                    </p>
                  </div>
                </div>
                <div className="flex flex-col items-end gap-2">
                  <button
                    onClick={toggleGlobalTrading}
                    disabled={isOffline}
                    className={`px-6 py-2 rounded-lg font-bold text-sm transition-all shadow-sm focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed ${controlState?.global_trading_enabled
                      ? 'bg-emerald-500 hover:bg-emerald-600 text-white ring-2 ring-emerald-200 hover:shadow-md'
                      : 'bg-rose-500 hover:bg-rose-600 text-white ring-2 ring-rose-200 hover:shadow-md'}`}
                  >
                    {controlState?.global_trading_enabled ? 'TRADING ON' : 'TRADING STOPPED'}
                  </button>
                  <span className="text-[10px] text-slate-400 uppercase tracking-widest font-bold">System Status</span>
                </div>
              </div>

              {/* Execution Mode */}
              <div className="flex items-center justify-between px-1">
                <div>
                  <h3 className="text-sm font-bold text-slate-800 flex items-center gap-2">
                    <ShieldAlert className="w-4 h-4 text-indigo-500" />
                    Execution Mode
                  </h3>
                  <p className="text-xs text-slate-500 mt-1">Controls signal intent (Practice vs Real Money)</p>
                </div>
                <div className="flex bg-slate-100 rounded-lg p-1 border border-slate-200">
                  {['DRY_RUN', 'LIVE'].map((mode) => (
                    <button
                      key={mode}
                      onClick={() => setExecutionMode(mode)}
                      disabled={isOffline}
                      className={`px-4 py-1.5 text-xs font-bold rounded-md transition-all focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-1 disabled:opacity-50 disabled:cursor-not-allowed ${controlState?.execution_mode === mode
                        ? 'bg-white shadow text-indigo-600 ring-1 ring-indigo-200'
                        : 'text-slate-500 hover:text-slate-700 hover:bg-slate-200/50'}`}
                    >
                      {mode}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </Card>

          {/* Routing Configuration */}
          <Card title="MT5 Output Routing" icon={Radio} className={isOffline ? 'opacity-60 grayscale pointer-events-none select-none' : ''}>
            <div className="flex justify-between items-center mb-4">
              <p className="text-sm text-slate-500">Manage active bridge connections and multipliers.</p>
              <button
                onClick={() => setShowAddOutput(!showAddOutput)}
                disabled={isOffline}
                className="text-xs bg-indigo-50 text-indigo-600 px-3 py-1.5 rounded-lg hover:bg-indigo-100 font-bold flex items-center gap-1.5 border border-indigo-100 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Plus className="w-3.5 h-3.5" /> Add Output
              </button>
            </div>

            {showAddOutput && (
              <div className="mb-4 p-4 bg-indigo-50/50 rounded-lg border border-indigo-100 cp-fade-in">
                <h3 className="text-xs font-bold text-indigo-800 mb-3 uppercase tracking-wide">New Route Configuration</h3>
                <div className="grid grid-cols-2 gap-3 mb-3">
                  <div className="col-span-2">
                    <label className="text-[10px] font-bold text-indigo-500 uppercase">Bridge Account ID</label>
                    <input className="w-full mt-0.5 text-xs border border-indigo-200 p-2 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:outline-none focus:border-indigo-400" placeholder="e.g. FTMO_DEMO_2" value={newOutput.bridge_account} onChange={(e) => setNewOutput({ ...newOutput, bridge_account: e.target.value })} />
                  </div>
                  <div>
                    <label className="text-[10px] font-bold text-indigo-500 uppercase">Lot Multiplier</label>
                    <input type="number" className="w-full mt-0.5 text-xs border border-indigo-200 p-2 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:outline-none" placeholder="1.0" value={newOutput.lot_multiplier} onChange={(e) => setNewOutput({ ...newOutput, lot_multiplier: parseFloat(e.target.value) })} />
                  </div>
                  <div>
                    <label className="text-[10px] font-bold text-indigo-500 uppercase">Max Daily Loss</label>
                    <input type="number" className="w-full mt-0.5 text-xs border border-indigo-200 p-2 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:outline-none" placeholder="500" value={newOutput.max_daily_loss} onChange={(e) => setNewOutput({ ...newOutput, max_daily_loss: parseFloat(e.target.value) })} />
                  </div>
                  <div>
                    <label className="text-[10px] font-bold text-indigo-500 uppercase">Max Trades</label>
                    <input type="number" className="w-full mt-0.5 text-xs border border-indigo-200 p-2 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:outline-none" placeholder="5" value={newOutput.max_trades_per_day} onChange={(e) => setNewOutput({ ...newOutput, max_trades_per_day: parseInt(e.target.value) })} />
                  </div>
                </div>
                <div className="flex justify-end gap-2">
                  <button onClick={() => setShowAddOutput(false)} className="px-3 py-1.5 text-xs font-medium text-slate-500 hover:bg-slate-100 rounded-lg transition-colors">Cancel</button>
                  <button onClick={handleAddOutput} className="px-3 py-1.5 text-xs font-bold bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 flex items-center gap-1.5 transition-colors">
                    <Save className="w-3 h-3" /> Save Route
                  </button>
                </div>
              </div>
            )}

            <div className="overflow-hidden rounded-lg border border-slate-200">
              <table className="w-full text-sm text-left">
                <thead className="text-xs text-slate-500 uppercase bg-slate-50/80 border-b border-slate-200">
                  <tr>
                    <th className="px-4 py-3 font-semibold">Bridge Account</th>
                    <th className="px-4 py-3 font-semibold text-center">Multiplier</th>
                    <th className="px-4 py-3 font-semibold text-right">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {routingConfig?.outputs.map((out, idx) => (
                    <tr key={idx} className="hover:bg-slate-50/60 transition-colors">
                      <td className="px-4 py-3 font-mono text-slate-700 text-xs font-medium">{out.bridge_account}</td>
                      <td className="px-4 py-3 text-center">
                        <input
                          type="number"
                          step="0.1"
                          className="w-16 border border-slate-200 rounded-md px-1.5 py-0.5 text-center text-xs font-mono focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none transition-all"
                          value={out.lot_multiplier}
                          onChange={(e) => updateMultiplier(idx, e.target.value)}
                        />
                      </td>
                      <td className="px-4 py-3 flex justify-end">
                        <button
                          onClick={() => toggleOutput(idx)}
                          className={`text-[10px] px-2.5 py-0.5 rounded-full font-bold uppercase tracking-wide border transition-all ${out.enabled
                            ? 'bg-emerald-50 text-emerald-600 border-emerald-200 hover:bg-emerald-100'
                            : 'bg-slate-50 text-slate-400 border-slate-200 hover:bg-slate-100'}`}
                        >
                          {out.enabled ? 'ACTIVE' : 'DISABLED'}
                        </button>
                      </td>
                    </tr>
                  ))}
                  {routingConfig?.outputs.length === 0 && (
                    <tr><td colSpan="3" className="text-center py-8 text-slate-400 text-xs">No output routes configured</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </Card>
        </section>

        <hr className="cp-section-divider" />

        {/* Bridge Status & Why No Trades */}
        <section className="grid grid-cols-1 lg:grid-cols-2 gap-6" aria-label="System Diagnostics">
          {/* Bridge Status */}
          <Card title="MT5 Bridge Status" icon={Radio}>
            {bridgeStatus ? (
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-semibold text-slate-700">Service Status</span>
                  <Badge variant={bridgeStatus.running ? 'success' : bridgeStatus.service_status === 'inactive' ? 'warning' : 'danger'}>
                    {bridgeStatus.running ? 'CONNECTED' : bridgeStatus.service_status === 'inactive' ? 'IDLE' : 'NOT RUNNING'}
                  </Badge>
                </div>
                {bridgeStatus.last_heartbeat && (
                  <div className="text-xs text-slate-600">
                    <span className="font-semibold">Last Heartbeat:</span>{' '}
                    {new Date(bridgeStatus.last_heartbeat).toLocaleString()}
                  </div>
                )}
                {bridgeStatus.last_message && (
                  <div className="text-xs text-slate-500 font-mono bg-slate-50 p-2 rounded border border-slate-200">
                    {bridgeStatus.last_message}
                  </div>
                )}
                {bridgeStatus.last_error && (
                  <div className="text-xs text-rose-600 bg-rose-50 p-2 rounded border border-rose-200">
                    <span className="font-semibold">Error:</span> {bridgeStatus.last_error}
                  </div>
                )}
                {!bridgeStatus.running && !bridgeStatus.last_heartbeat && (
                  <div className="text-xs text-amber-600 bg-amber-50 p-2 rounded border border-amber-200">
                    Bridge service not detected. Check systemd service or process list.
                  </div>
                )}
              </div>
            ) : (
              <div className="text-center py-4 text-slate-400 text-sm">
                <Radio className="w-6 h-6 mx-auto mb-2 opacity-25" />
                <p>Bridge status unavailable</p>
              </div>
            )}
          </Card>

          {/* Why No Trades */}
          {systemStatus?.last_signals_generated === 0 && whyNoTrades && (
            <Card title="Why No Trades?" icon={AlertTriangle}>
              <div className="space-y-3">
                <div className="text-xs text-slate-600 mb-3">
                  <span className="font-semibold">Last Scan:</span>{' '}
                  {systemStatus.last_scan_at ? new Date(systemStatus.last_scan_at).toLocaleString() : 'Unknown'}
                </div>
                {whyNoTrades.instruments && Object.keys(whyNoTrades.instruments).length > 0 ? (
                  <div className="space-y-2 max-h-64 overflow-y-auto">
                    {Object.entries(whyNoTrades.instruments).map(([instrument, data]) => (
                      <div key={instrument} className="bg-slate-50 rounded-lg p-3 border border-slate-200">
                        <div className="flex items-center justify-between mb-2">
                          <span className="font-mono text-sm font-bold text-slate-800">{instrument}</span>
                          {data.last_blocked_at && (
                            <span className="text-[10px] text-slate-400">
                              {new Date(data.last_blocked_at).toLocaleTimeString()}
                            </span>
                          )}
                        </div>
                        <div className="space-y-1">
                          {data.reasons && data.reasons.length > 0 ? (
                            data.reasons.map((reason, idx) => (
                              <div key={idx} className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded px-2 py-1">
                                {reason.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                              </div>
                            ))
                          ) : (
                            <div className="text-xs text-slate-500">No blocking reasons found</div>
                          )}
                        </div>
                        {data.bias_state && (
                          <div className="mt-2 pt-2 border-t border-slate-200">
                            <div className="text-[10px] text-slate-400">
                              <span className="font-semibold">Bias:</span> {data.bias_state.final_bias || 'NEUTRAL'}
                            </div>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-4 text-slate-400 text-sm">
                    <AlertTriangle className="w-6 h-6 mx-auto mb-2 opacity-25" />
                    <p>No instrument blocking data available</p>
                  </div>
                )}
              </div>
            </Card>
          )}
        </section>

        {systemStatus?.last_signals_generated === 0 && whyNoTrades && <hr className="cp-section-divider" />}

        {/* System Thinking - Continuous Signal-Level Status */}
        <section aria-label="System Thinking">
          <Card title="System Thinking (Signals)" icon={Activity}>
            {(!signalThinking || !signalThinking.thinking || Object.keys(signalThinking.thinking).length === 0) ? (
              <div className="text-center py-8 text-slate-400 text-sm">
                <Activity className="w-8 h-8 mx-auto mb-2 opacity-25" />
                <p>Waiting for signal evaluations... This panel will show per-instrument status even when no trades fire.</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {Object.entries(signalThinking.thinking).map(([instrument, info]) => {
                  const status = info.status || 'scanning';
                  let variant = 'neutral';
                  let label = 'SCANNING';
                  if (status === 'ready') {
                    variant = 'success';
                    label = 'READY';
                  } else if (status === 'blocked') {
                    variant = 'danger';
                    label = 'BLOCKED';
                  } else if (status === 'near_miss') {
                    variant = 'warning';
                    label = 'NEAR MISS';
                  } else if (status === 'evaluating') {
                    variant = 'info';
                    label = 'SCANNING';
                  }

                  const ts = info.last_update ? new Date(info.last_update) : null;
                  const reason = info.reason || info.details?.reason;

                  return (
                    <div key={instrument} className="bg-slate-50 rounded-lg border border-slate-200 p-4 hover:shadow-md hover:border-slate-300 transition-all">
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-mono text-sm font-bold text-slate-800">{instrument}</span>
                        <Badge variant={variant}>{label}</Badge>
                      </div>
                      <div className="text-xs text-slate-500 space-y-1">
                        <div>
                          <span className="font-semibold">Strategy:</span>{' '}
                          <span className="font-mono">{info.strategy || 'UNKNOWN'}</span>
                        </div>
                        {reason && (
                          <div>
                            <span className="font-semibold">Last Reason:</span>{' '}
                            <span className="font-mono break-all">
                              {String(reason).replace(/_/g, ' ')}
                            </span>
                          </div>
                        )}
                        {typeof info.score === 'number' && (
                          <div>
                            <span className="font-semibold">Readiness Score:</span>{' '}
                            <span className="font-mono">{info.score}</span>
                          </div>
                        )}
                        <div>
                          <span className="font-semibold">Last Evaluation:</span>{' '}
                          <span className="font-mono">
                            {ts ? ts.toLocaleTimeString() : 'UNKNOWN'}
                          </span>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </Card>
        </section>

        {/* Session Gate & Reasoning (S3: Dashboard Wiring) */}
        <section aria-label="Session Gate & Reasoning">
          <Card
            title="Readiness & Reasoning"
            icon={ShieldAlert}
          >
            {Object.keys(readinessObservability).length === 0 ? (
              <div className="text-center py-6 text-slate-400 text-sm">
                <ShieldAlert className="w-6 h-6 mx-auto mb-2 opacity-25" />
                <p>No readiness data available yet. Waiting for system scan...</p>
              </div>
            ) : (
              <div>
                 {Object.entries(readinessObservability).map(([instrument, data]) => (
                    <ReadinessPanel key={instrument} instrument={instrument} data={data} />
                 ))}
              </div>
            )}
          </Card>
        </section>

        {/* Gate Proximity & Why No Trades (Unified Visibility) */}
        <section aria-label="Gate Proximity & Why No Trades">
          <Card
            title="Gate Proximity & Why No Trades"
            icon={AlertTriangle}
            className={
              systemStatus?.last_signals_generated === 0
                ? 'ring-2 ring-amber-300 ring-offset-2 ring-offset-slate-50'
                : ''
            }
          >
            {!gateProximity || !gateProximity.instruments || Object.keys(gateProximity.instruments).length === 0 ? (
              <div className="text-center py-6 text-slate-400 text-sm">
                <AlertTriangle className="w-6 h-6 mx-auto mb-2 opacity-25" />
                <p>No gate proximity data available yet. This panel will fill once Alpha has completed at least one scan.</p>
              </div>
            ) : (
              <div className="space-y-4">
                <div className="flex items-center justify-between text-xs text-slate-500">
                  <div>
                    <span className="font-semibold">Snapshot:</span>{' '}
                    {gateProximity.timestamp ? new Date(gateProximity.timestamp).toLocaleTimeString() : 'Unknown'}
                  </div>
                  {systemStatus && (
                    <div>
                      <span className="font-semibold">Last Scan:</span>{' '}
                      {systemStatus.last_scan_at ? new Date(systemStatus.last_scan_at).toLocaleTimeString() : 'Unknown'}
                    </div>
                  )}
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {Object.entries(gateProximity.instruments).map(([instrument, data]) => {
                    const proximity = typeof data.proximity_score === 'number' ? data.proximity_score : 0;
                    const bias = (data.final_bias || 'neutral').toUpperCase();
                    const variant =
                      proximity >= 90 ? 'success' :
                      proximity >= 60 ? 'warning' :
                      'danger';

                    return (
                      <div
                        key={instrument}
                        className="bg-slate-50 rounded-lg border border-slate-200 p-4 hover:shadow-md hover:border-slate-300 transition-all"
                      >
                        <div className="flex items-center justify-between mb-2">
                          <span className="font-mono text-sm font-bold text-slate-800">{instrument}</span>
                          <Badge variant={variant}>
                            {bias}
                          </Badge>
                        </div>
                        <div className="mb-2">
                          <div className="flex items-center justify-between text-[10px] text-slate-500 mb-1">
                            <span>Proximity to Flip</span>
                            <span className="font-mono">{proximity}%</span>
                          </div>
                          <div className="h-2 rounded-full bg-slate-200 overflow-hidden">
                            <div
                              className={
                                `h-full rounded-full transition-all duration-500 ` +
                                (proximity >= 90
                                  ? 'bg-emerald-500'
                                  : proximity >= 60
                                  ? 'bg-amber-500'
                                  : 'bg-rose-500')
                              }
                              style={{ width: `${Math.max(0, Math.min(100, proximity))}%` }}
                            />
                          </div>
                        </div>
                        {data.blocking_sources && data.blocking_sources.length > 0 && (
                          <div className="mb-2">
                            <div className="text-[10px] font-bold text-amber-700 uppercase tracking-wide mb-1">
                              Blocking Sources
                            </div>
                            <div className="space-y-1">
                              {data.blocking_sources.map((src, idx) => (
                                <div
                                  key={idx}
                                  className="text-[10px] text-amber-800 bg-amber-50 border border-amber-200 rounded px-2 py-0.5"
                                >
                                  {src}
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                        {data.last_blocked_at && (
                          <div className="text-[10px] text-slate-400 mb-1">
                            <span className="font-semibold">Last Blocked:</span>{' '}
                            {new Date(data.last_blocked_at).toLocaleTimeString()}
                          </div>
                        )}
                        {data.next_unlock_hint && (
                          <div className="text-[10px] text-slate-500 mt-1">
                            <span className="font-semibold">Next Unlock Hint:</span>{' '}
                            <span className="font-mono break-words">
                              {data.next_unlock_hint}
                            </span>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </Card>
        </section>

        {/* Bias Observability */}
        <section aria-label="Bias Observability">
          <Card title="Bias Observability" icon={Activity}>
            <div className="space-y-4">
              {biasStates.length === 0 ? (
                <div className="text-center py-8 text-slate-400 text-sm">
                  <Activity className="w-8 h-8 mx-auto mb-2 opacity-25" />
                  <p>No bias state data available. Bias states will appear here after Alpha scan cycles.</p>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {biasStates.map((bias, idx) => {
                    const isExpanded = expandedBias.has(bias.instrument);
                    const finalBias = bias.final_bias?.toUpperCase() || 'NEUTRAL';
                    const biasVariant =
                      finalBias === 'BULLISH' ? 'success' :
                        finalBias === 'BEARISH' ? 'danger' :
                          finalBias === 'BLOCKED' ? 'warning' :
                            'neutral';

                    return (
                      <div key={idx} className="bg-slate-50 rounded-lg border border-slate-200 p-4 hover:shadow-md hover:border-slate-300 transition-all">
                        <div className="flex items-center justify-between mb-3">
                          <div className="flex items-center gap-2">
                            <span className="font-mono text-sm font-bold text-slate-800">{bias.instrument}</span>
                            <Badge variant={biasVariant}>{finalBias}</Badge>
                          </div>
                          <button
                            onClick={() => {
                              const next = new Set(expandedBias);
                              if (isExpanded) next.delete(bias.instrument);
                              else next.add(bias.instrument);
                              setExpandedBias(next);
                            }}
                            className="p-1 rounded text-slate-400 hover:text-slate-600 hover:bg-slate-200/50 transition-colors"
                            aria-expanded={isExpanded}
                          >
                            {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                          </button>
                        </div>

                        <div className="text-xs text-slate-500 mb-2">
                          <span className="font-semibold">Regime:</span> {bias.regime || 'UNKNOWN'}
                        </div>

                        {bias.blocking_sources && bias.blocking_sources.length > 0 && (
                          <div className="mb-2">
                            <span className="inline-flex items-center gap-1 text-[10px] font-bold text-amber-700 bg-amber-50 border border-amber-200 rounded-full px-2 py-0.5">
                              <AlertTriangle className="w-3 h-3" /> {bias.blocking_sources.length} Blocking
                            </span>
                          </div>
                        )}

                        {isExpanded && (
                          <div className="mt-3 pt-3 border-t border-slate-200 space-y-2 cp-fade-in">
                            <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wide mb-2">Bias Sources</div>
                            {bias.sources && Object.entries(bias.sources).map(([sourceName, sourceData]) => (
                              <div key={sourceName} className="cp-bias-source bg-white rounded-lg p-2 border border-slate-100">
                                <div className="flex items-center justify-between mb-1">
                                  <span className="text-xs font-semibold text-slate-600 capitalize">{sourceName.replace(/_/g, ' ')}</span>
                                  <Badge variant={sourceData.status === 'unavailable' ? 'neutral' : 'info'}>{sourceData.status || 'unknown'}</Badge>
                                </div>
                                {sourceData.strength != null && (
                                  <div className="text-[10px] text-slate-500">Strength: {Number(sourceData.strength).toFixed(3)}</div>
                                )}
                                {sourceData.reason && (
                                  <div className="text-[10px] text-slate-400 mt-1 truncate" title={sourceData.reason}>{sourceData.reason}</div>
                                )}
                              </div>
                            ))}
                            {bias.blocking_sources && bias.blocking_sources.length > 0 && (
                              <div className="mt-2 pt-2 border-t border-slate-200">
                                <div className="text-[10px] font-bold text-amber-600 uppercase tracking-wide mb-1">Blocking Sources</div>
                                <div className="space-y-1">
                                  {bias.blocking_sources.map((block, i) => (
                                    <div key={i} className="cp-bias-source cp-bias-blocking text-[10px] text-amber-800 rounded px-2 py-1">
                                      {block}
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}
                            <div className="text-[10px] text-slate-400 mt-2">
                              Updated: {new Date(bias.timestamp).toLocaleTimeString()}
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </Card>
        </section>

        <hr className="cp-section-divider" />

        {/* Logs */}
        <section className="grid grid-cols-1 lg:grid-cols-2 gap-6" aria-label="Logs">
          <LogPanel title="Alpha Signals Feed" logs={alphaLogs} emptyMessage="Waiting for trading signals..." />
          <LogPanel title="MT5 Bridge Feedback" logs={bridgeLogs} emptyMessage="No bridge activity detected..." />
        </section>
      </main>

      {toast && (
        <div
          role="alert"
          className={`cp-toast fixed bottom-6 right-6 z-30 px-4 py-3 rounded-lg shadow-lg border flex items-center gap-2 ${
            toast.variant === 'danger' ? 'bg-rose-50 border-rose-200 text-rose-800' : 'bg-emerald-50 border-emerald-200 text-emerald-800'
          }`}
        >
          {toast.variant === 'danger' ? <AlertTriangle className="w-4 h-4 shrink-0" /> : <Save className="w-4 h-4 shrink-0" />}
          <span className="text-sm font-medium">{toast.message}</span>
        </div>
      )}
    </div>
  );
}
