import React, { useEffect, useMemo, useState } from "react";
import {
  Activity,
  Sliders,
  FileText,
  RefreshCw,
  Save,
  Shield,
  AlertTriangle,
  X
} from "lucide-react";
import { getJSON, apiPut } from '../api/client';

const API = "/api";
const CONFIRM_PHRASE = "APPLY_STRATEGY_ASSIGNMENTS";

function safeGet(obj, path, fallback = undefined) {
  try {
    return path.split(".").reduce((acc, k) => (acc == null ? acc : acc[k]), obj) ?? fallback;
  } catch {
    return fallback;
  }
}

function unwrapData(json) {
  if (json != null && typeof json === "object" && "data" in json && json.data !== undefined) return json.data;
  return json;
}

function mapModeToUi(mode) {
  if (mode === "QUALITY_OVER_SPEED") return "QUALITY_OVER_SPEED";
  if (mode === "SPEED") return "SPEED_OVER_QUALITY";
  if (mode === "TOP_N_DAILY") return "BALANCED";
  return "BALANCED";
}

function mapCutoffToUi(cutoff) {
  if (cutoff === "IMMEDIATE") return "IMMEDIATE";
  // runner uses NY_CLOSE; UI schema uses SESSION_END/DAY_END
  return "SESSION_END";
}

export default function ControlPlaneMvp({ embedded = false } = {}) {
  const [tab, setTab] = useState("status"); // status | controls | commandPack

  const [statusData, setStatusData] = useState(null);
  const [configData, setConfigData] = useState(null);
  const [schemaData, setSchemaData] = useState(null);
  const [commandPackData, setCommandPackData] = useState(null);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [reason, setReason] = useState("");
  const [saving, setSaving] = useState(false);
  const [saveResult, setSaveResult] = useState(null);

  const [form, setForm] = useState(null);
  const [token, setToken] = useState("");

  const [confirming, setConfirming] = useState(false);
  const [confirmInput, setConfirmInput] = useState("");

  const loadAll = async () => {
    try {
      setError(null);
      
      const stRes = await getJSON(`${API}/status`);
      const cfgRes = await getJSON(`${API}/config`);
      const schRes = await getJSON(`${API}/controls/schema`);
      
      const st = stRes.ok ? unwrapData(stRes.data) : null;
      const cfg = cfgRes.ok ? unwrapData(cfgRes.data) : null;
      const sch = schRes.ok ? unwrapData(schRes.data) : null;

      setStatusData(st);
      setConfigData(cfg);
      setSchemaData(sch);
      setLoading(false);

      if (!stRes.ok || !cfgRes.ok) {
         setError(stRes.error || cfgRes.error || "Failed to load data");
      }

      // Initialize form only once per load (source of truth: /api/config)
      const cfgData = cfg || {};
      const guards = cfgData.guards || {};
      const tradeSel = cfgData.trade_selection || {};
      const execPol = cfgData.execution_policy || {};

      setForm({
        risk: { ...(cfgData.risk || {}) },
        trade_selection: {
          ...tradeSel,
          mode: mapModeToUi(tradeSel.mode),
          execution_cutoff: mapCutoffToUi(tradeSel.execution_cutoff),
        },
        execution_policy: { ...execPol },
        strategy_assignments: Array.isArray(cfgData.strategy_assignments) ? cfgData.strategy_assignments : null,
        guards: {
          enabled: guards.enabled ?? true,
          default_profile: guards.default_profile ?? "DEV",
          account_overrides: { ...(guards.account_overrides || {}) },
          strategy_overrides: { ...(guards.strategy_overrides || {}) },
          feature_toggles: { ...(guards.feature_toggles || {}) },
        },
      });
    } catch (e) {
      setError(String(e?.message || e));
      setLoading(false);
    }
  };

  const loadCommandPack = async () => {
    try {
      const res = await getJSON(`${API}/command-pack`);
      if (res.ok) {
          setCommandPackData(unwrapData(res.data));
      } else {
          setCommandPackData({ ok: false, error: res.error });
      }
    } catch (e) {
      setCommandPackData({ ok: false, error: String(e?.message || e) });
    }
  };

  useEffect(() => {
    loadAll();
    const t = setInterval(async () => {
      try {
        const res = await getJSON(`${API}/status`, { timeoutMs: 2000 });
        if (res.ok) setStatusData(unwrapData(res.data));
      } catch {
        // keep last known status
      }
    }, 5000);
    return () => clearInterval(t);
  }, []);

  useEffect(() => {
    if (tab === "commandPack" && commandPackData == null) loadCommandPack();
  }, [tab]);

  const effectiveGuards = useMemo(() => {
    return safeGet(statusData, "effective_guards", []) || [];
  }, [statusData]);

  const requestedConfig = useMemo(() => configData || {}, [configData]);
  const controlsSchema = useMemo(() => schemaData?.schema || null, [schemaData]);

  const initiateSave = () => {
      setConfirming(true);
      setConfirmInput("");
      setSaveResult(null);
  };

  const cancelSave = () => {
      setConfirming(false);
      setConfirmInput("");
  };

  const performSave = async () => {
    if (!form) return;
    if (confirmInput !== CONFIRM_PHRASE) {
        setSaveResult({ ok: false, error: `Incorrect confirm phrase. Expected: ${CONFIRM_PHRASE}` });
        return;
    }
    
    setConfirming(false);
    setSaving(true);
    setSaveResult(null);
    try {
      // Build minimal patch: only include sections we control
      const patch = {
        risk: form.risk,
        trade_selection: form.trade_selection,
        execution_policy: {
          signals_only: !!form.execution_policy?.signals_only,
          paper_execution_enabled: !!form.execution_policy?.paper_execution_enabled,
          live_trading_allowed: false, // locked on ALPHA
        },
        ...(Array.isArray(form.strategy_assignments) ? { strategy_assignments: form.strategy_assignments } : {}),
        guards: {
          enabled: !!form.guards?.enabled,
          default_profile: form.guards?.default_profile,
          account_overrides: form.guards?.account_overrides || {},
          strategy_overrides: form.guards?.strategy_overrides || {},
          feature_toggles: form.guards?.feature_toggles || {},
        },
      };

      const res = await apiPut(`${API}/config/patch`, 
        { reason: reason || "dashboard_patch", patch, config_reload_mode: "restart" },
        token
      );
      
      if (res.ok) {
          setSaveResult(res.data);
          await loadAll();
      } else {
          setSaveResult({ ok: false, error: res.error || `HTTP ${res.status}` });
      }
    } catch (e) {
      setSaveResult({ ok: false, error: String(e?.message || e) });
    } finally {
      setSaving(false);
    }
  };

  const NavButton = ({ id, icon: Icon, label }) => (
    <button
      onClick={() => setTab(id)}
      className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-semibold border ${
        tab === id ? "bg-slate-900 text-white border-slate-700" : "bg-white text-slate-800 border-slate-200"
      }`}
    >
      <Icon className="w-4 h-4" />
      {label}
    </button>
  );

  if (loading) {
    return (
      <div className="p-6 text-slate-200">
        <div className="text-sm opacity-80">Loading Control Plane…</div>
      </div>
    );
  }

  return (
    <div className={embedded ? "bg-slate-950 text-slate-100 relative" : "min-h-screen bg-slate-950 text-slate-100 relative"}>
      
      {/* Confirm Modal */}
      {confirming && (
        <div className="absolute inset-0 z-50 flex items-center justify-center bg-black/80 p-4">
            <div className="bg-slate-900 border border-slate-700 rounded-xl p-6 max-w-md w-full shadow-2xl">
                <div className="flex justify-between items-center mb-4">
                    <h3 className="text-lg font-bold text-white flex items-center gap-2">
                        <AlertTriangle className="w-5 h-5 text-amber-500"/> Confirm Apply
                    </h3>
                    <button onClick={cancelSave} className="text-slate-400 hover:text-white"><X className="w-5 h-5"/></button>
                </div>
                <p className="text-sm text-slate-300 mb-4">
                    You are about to patch the system configuration. This may restart the runner.
                    <br/><br/>
                    Type <span className="font-mono font-bold text-white select-all">{CONFIRM_PHRASE}</span> to confirm.
                </p>
                <input 
                    value={confirmInput}
                    onChange={e => setConfirmInput(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-700 rounded p-2 mb-4 font-mono text-sm"
                    placeholder="Type phrase here..."
                />
                <div className="flex gap-3 justify-end">
                    <button onClick={cancelSave} className="px-4 py-2 rounded text-sm text-slate-400 hover:text-white">Cancel</button>
                    <button 
                        onClick={performSave} 
                        disabled={confirmInput !== CONFIRM_PHRASE}
                        className="px-4 py-2 rounded text-sm font-bold bg-amber-600 text-white disabled:opacity-50 hover:bg-amber-500"
                    >
                        APPLY PATCH
                    </button>
                </div>
            </div>
        </div>
      )}

      <div className={embedded ? "mx-auto flex gap-6" : "max-w-7xl mx-auto p-6 flex gap-6"}>
        {/* Left nav */}
        <div className="w-64 shrink-0">
          <div className="mb-4">
            <div className="text-xs uppercase tracking-wider text-slate-400">Control Plane</div>
            <div className="text-lg font-black">Dashboard MVP</div>
          </div>
          <div className="space-y-2">
            <NavButton id="status" icon={Activity} label="Status" />
            <NavButton id="controls" icon={Sliders} label="Controls" />
            <NavButton id="commandPack" icon={FileText} label="Command Pack" />
          </div>

          <div className="mt-6 p-3 rounded-lg border border-slate-800 bg-slate-900/40">
            <div className="text-xs font-bold text-slate-300 mb-2 flex items-center gap-2">
              <Shield className="w-4 h-4" /> Auth (optional)
            </div>
            <input
              value={token}
              onChange={(e) => setToken(e.target.value)}
              placeholder="Bearer token (if configured)"
              className="w-full bg-slate-950 border border-slate-800 rounded px-2 py-1 text-xs font-mono"
            />
            <div className="text-[11px] text-slate-400 mt-2">
              If `CONTROL_PLANE_TOKEN` is set, enter it here to enable PATCH.
            </div>
          </div>
        </div>

        {/* Main */}
        <div className="flex-1">
          {error && (
            <div className="mb-4 p-3 rounded-lg border border-rose-800 bg-rose-950/40 text-rose-200 text-sm">
              {error}
            </div>
          )}

          <div className="flex items-center justify-between mb-4">
            <div className="text-sm text-slate-300">
              system_label: <span className="font-mono text-slate-100">{safeGet(statusData, "system_label", "UNKNOWN")}</span>{" "}
              · mode: <span className="font-mono text-slate-100">{safeGet(statusData, "mode", "paper")}</span>{" "}
              · execution_enabled: <span className="font-mono text-slate-100">{String(safeGet(statusData, "execution_enabled", false))}</span>
            </div>
            <button
              onClick={loadAll}
              className="inline-flex items-center gap-2 px-3 py-2 rounded-lg border border-slate-800 bg-slate-900/40 text-sm font-bold"
            >
              <RefreshCw className="w-4 h-4" /> Refresh
            </button>
          </div>

          {tab === "status" && (
            <div className="space-y-4">
              <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/30">
                <div className="text-xs uppercase tracking-wider text-slate-400 mb-3">Effective Guards</div>
                {effectiveGuards.length === 0 ? (
                  <div className="text-sm text-slate-400">No effective guards emitted.</div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="text-left text-slate-400 border-b border-slate-800">
                          <th className="py-2 pr-4">account_id</th>
                          <th className="py-2 pr-4">strategy</th>
                          <th className="py-2 pr-4">profile</th>
                          <th className="py-2 pr-4">precedence</th>
                          <th className="py-2 pr-4">toggles</th>
                        </tr>
                      </thead>
                      <tbody>
                        {effectiveGuards.map((g) => (
                          <tr key={g.account_id} className="border-b border-slate-900">
                            <td className="py-2 pr-4 font-mono">{g.account_id}</td>
                            <td className="py-2 pr-4 font-mono">{g.assigned_strategy}</td>
                            <td className="py-2 pr-4 font-mono">{g.guard_profile_effective}</td>
                            <td className="py-2 pr-4 font-mono">{g.precedence_used}</td>
                            <td className="py-2 pr-4 font-mono text-xs">
                              {Object.entries(g.toggles_effective || {})
                                .map(([k, v]) => `${k}=${v ? "1" : "0"}`)
                                .join(" · ")}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>

              <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/30">
                <div className="text-xs uppercase tracking-wider text-slate-400 mb-3">Requested Config (selected)</div>
                <pre className="text-xs font-mono text-slate-200 whitespace-pre-wrap">
                  {JSON.stringify(
                    {
                      execution_policy: requestedConfig.execution_policy,
                      risk: requestedConfig.risk,
                      trade_selection: requestedConfig.trade_selection,
                      guards: requestedConfig.guards,
                    },
                    null,
                    2
                  )}
                </pre>
              </div>
            </div>
          )}

          {tab === "controls" && (
            <div className="space-y-4">
              <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/30">
                <div className="text-xs uppercase tracking-wider text-slate-400 mb-3">Controls Schema</div>
                {!controlsSchema ? (
                  <div className="text-sm text-slate-400">Schema missing.</div>
                ) : (
                  <pre className="text-xs font-mono text-slate-200 whitespace-pre-wrap">{JSON.stringify(controlsSchema, null, 2)}</pre>
                )}
              </div>

              <div id="control-preview-diff" className="hidden" aria-hidden="true" />
              <div id="control-strategy-editor" className="p-4 rounded-xl border border-slate-800 bg-slate-900/30 space-y-4">
                <div className="flex items-center justify-between">
                  <div className="text-xs uppercase tracking-wider text-slate-400">Patch Controls</div>
                  <button
                    id="control-apply-button"
                    disabled={saving}
                    onClick={initiateSave}
                    className="inline-flex items-center gap-2 px-3 py-2 rounded-lg border border-slate-800 bg-slate-900/40 text-sm font-black disabled:opacity-50 hover:bg-slate-800"
                  >
                    <Save className="w-4 h-4" /> {saving ? "Saving…" : "Save (PATCH)"}
                  </button>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <div className="text-sm font-black mb-2">Risk</div>
                    {["max_risk_per_trade_pct", "max_positions", "max_daily_loss_pct", "max_drawdown_pct", "max_daily_trades_per_account"].map((k) => (
                      <label key={k} className="block mb-2 text-xs text-slate-300">
                        {k}
                        <input
                          value={form?.risk?.[k] ?? ""}
                          onChange={(e) => setForm((f) => ({ ...f, risk: { ...f.risk, [k]: e.target.value === "" ? "" : Number(e.target.value) } }))}
                          type="number"
                          className="mt-1 w-full bg-slate-950 border border-slate-800 rounded px-2 py-1 text-xs font-mono"
                        />
                      </label>
                    ))}
                  </div>

                  <div>
                    <div className="text-sm font-black mb-2">Trade Selection</div>
                    <label className="block mb-2 text-xs text-slate-300">
                      mode
                      <select
                        value={form?.trade_selection?.mode ?? "BALANCED"}
                        onChange={(e) => setForm((f) => ({ ...f, trade_selection: { ...f.trade_selection, mode: e.target.value } }))}
                        className="mt-1 w-full bg-slate-950 border border-slate-800 rounded px-2 py-1 text-xs font-mono"
                      >
                        {["QUALITY_OVER_SPEED", "SPEED_OVER_QUALITY", "BALANCED"].map((m) => (
                          <option key={m} value={m}>
                            {m}
                          </option>
                        ))}
                      </select>
                    </label>
                    {["daily_trade_limit", "min_confidence_threshold", "early_session_penalty_minutes", "exceptional_confidence_threshold"].map((k) => (
                      <label key={k} className="block mb-2 text-xs text-slate-300">
                        {k}
                        <input
                          value={form?.trade_selection?.[k] ?? ""}
                          onChange={(e) =>
                            setForm((f) => ({
                              ...f,
                              trade_selection: { ...f.trade_selection, [k]: e.target.value === "" ? "" : Number(e.target.value) },
                            }))
                          }
                          type="number"
                          className="mt-1 w-full bg-slate-950 border border-slate-800 rounded px-2 py-1 text-xs font-mono"
                        />
                      </label>
                    ))}
                    <label className="inline-flex items-center gap-2 text-xs text-slate-300">
                      <input
                        type="checkbox"
                        checked={!!form?.trade_selection?.re_rank_on_each_scan}
                        onChange={(e) => setForm((f) => ({ ...f, trade_selection: { ...f.trade_selection, re_rank_on_each_scan: e.target.checked } }))}
                      />
                      re_rank_on_each_scan
                    </label>
                    <div className="mt-2" />
                    <label className="inline-flex items-center gap-2 text-xs text-slate-300">
                      <input
                        type="checkbox"
                        checked={!!form?.trade_selection?.allow_exceptional_early_execution}
                        onChange={(e) =>
                          setForm((f) => ({
                            ...f,
                            trade_selection: { ...f.trade_selection, allow_exceptional_early_execution: e.target.checked },
                          }))
                        }
                      />
                      allow_exceptional_early_execution
                    </label>
                    <label className="block mt-2 text-xs text-slate-300">
                      execution_cutoff
                      <select
                        value={form?.trade_selection?.execution_cutoff ?? "SESSION_END"}
                        onChange={(e) => setForm((f) => ({ ...f, trade_selection: { ...f.trade_selection, execution_cutoff: e.target.value } }))}
                        className="mt-1 w-full bg-slate-950 border border-slate-800 rounded px-2 py-1 text-xs font-mono"
                      >
                        {["IMMEDIATE", "SESSION_END", "DAY_END"].map((m) => (
                          <option key={m} value={m}>
                            {m}
                          </option>
                        ))}
                      </select>
                    </label>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <div className="text-sm font-black mb-2">Execution Policy</div>
                    <label id="control-alerts-mode" className="inline-flex items-center gap-2 text-xs text-slate-300">
                      <input
                        data-testid="switch-signals-only"
                        type="checkbox"
                        checked={!!form?.execution_policy?.signals_only}
                        onChange={(e) => setForm((f) => ({ ...f, execution_policy: { ...f.execution_policy, signals_only: e.target.checked } }))}
                      />
                      signals_only
                    </label>
                    <div className="mt-2" />
                    <label id="control-execution-toggle" className="inline-flex items-center gap-2 text-xs text-slate-300">
                      <input
                        data-testid="switch-paper-execution"
                        type="checkbox"
                        checked={!!form?.execution_policy?.paper_execution_enabled}
                        onChange={(e) =>
                          setForm((f) => ({
                            ...f,
                            execution_policy: { ...f.execution_policy, paper_execution_enabled: e.target.checked },
                          }))
                        }
                      />
                      paper_execution_enabled
                    </label>
                    <div className="mt-2 text-xs text-slate-500 font-mono">live_trading_allowed is locked false on ALPHA</div>

                    <div className="mt-4 text-sm font-black mb-2">Strategy Assignments</div>
                    {!Array.isArray(form?.strategy_assignments) ? (
                      <div className="text-xs text-slate-400">No strategy_assignments configured.</div>
                    ) : form.strategy_assignments.length === 0 ? (
                      <div className="text-xs text-slate-400">strategy_assignments is empty.</div>
                    ) : (
                      <div className="space-y-2">
                        {form.strategy_assignments.map((a, idx) => (
                          <div key={`${a.account_id || "acct"}-${idx}`} className="p-2 rounded border border-slate-800 bg-slate-950/40">
                            <div className="text-xs font-mono text-slate-200">{a.account_id}</div>
                            <div className="text-xs font-mono text-slate-400">{a.strategy_key}</div>
                            <label className="inline-flex items-center gap-2 text-xs text-slate-300 mt-2">
                              <input
                                type="checkbox"
                                checked={!!a.enabled}
                                onChange={(e) =>
                                  setForm((f) => ({
                                    ...f,
                                    strategy_assignments: f.strategy_assignments.map((x, j) =>
                                      j === idx ? { ...x, enabled: e.target.checked } : x
                                    ),
                                  }))
                                }
                              />
                              enabled
                            </label>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  <div>
                    <div className="text-sm font-black mb-2">Guards</div>
                    <label className="inline-flex items-center gap-2 text-xs text-slate-300">
                      <input
                        type="checkbox"
                        checked={!!form?.guards?.enabled}
                        onChange={(e) => setForm((f) => ({ ...f, guards: { ...f.guards, enabled: e.target.checked } }))}
                      />
                      guards.enabled
                    </label>
                    <label className="block mt-2 text-xs text-slate-300">
                      default_profile
                      <select
                        value={form?.guards?.default_profile ?? "DEV"}
                        onChange={(e) => setForm((f) => ({ ...f, guards: { ...f.guards, default_profile: e.target.value } }))}
                        className="mt-1 w-full bg-slate-950 border border-slate-800 rounded px-2 py-1 text-xs font-mono"
                      >
                        {["DEV", "PROP_SAFE"].map((p) => (
                          <option key={p} value={p}>
                            {p}
                          </option>
                        ))}
                      </select>
                    </label>
                    <div className="mt-3 text-xs uppercase tracking-wider text-slate-400">feature_toggles</div>
                    {["session_filter_enabled", "day_filter_enabled", "news_embargo_enabled", "top3_per_session_enabled"].map((k) => (
                      <label key={k} className="flex items-center gap-2 text-xs text-slate-300 mt-2">
                        <input
                          type="checkbox"
                          checked={!!form?.guards?.feature_toggles?.[k]}
                          onChange={(e) =>
                            setForm((f) => ({
                              ...f,
                              guards: {
                                ...f.guards,
                                feature_toggles: { ...(f.guards?.feature_toggles || {}), [k]: e.target.checked },
                              },
                            }))
                          }
                        />
                        {k}
                      </label>
                    ))}
                  </div>
                </div>

                <div className="p-3 rounded-lg border border-slate-800 bg-slate-950/40">
                  <div className="text-xs uppercase tracking-wider text-slate-400 mb-2">Account Overrides</div>
                  {effectiveGuards.length === 0 ? (
                    <div className="text-sm text-slate-400">No accounts visible. (Check allowlist / assignments.)</div>
                  ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      {effectiveGuards.map((g) => (
                        <label key={g.account_id} className="text-xs text-slate-300">
                          {g.account_id}
                          <select
                            value={form?.guards?.account_overrides?.[g.account_id] ?? ""}
                            onChange={(e) =>
                              setForm((f) => ({
                                ...f,
                                guards: {
                                  ...f.guards,
                                  account_overrides: { ...(f.guards?.account_overrides || {}), [g.account_id]: e.target.value },
                                },
                              }))
                            }
                            className="mt-1 w-full bg-slate-950 border border-slate-800 rounded px-2 py-1 text-xs font-mono"
                          >
                            <option value="">(unset)</option>
                            <option value="DEV">DEV</option>
                            <option value="PROP_SAFE">PROP_SAFE</option>
                          </select>
                          <div className="text-[11px] text-slate-500 font-mono mt-1">effective: {g.guard_profile_effective}</div>
                        </label>
                      ))}
                    </div>
                  )}
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <label className="block text-xs text-slate-300">
                    Reason (audit)
                    <input
                      value={reason}
                      onChange={(e) => setReason(e.target.value)}
                      placeholder="e.g. TEST: set 006 DEV"
                      className="mt-1 w-full bg-slate-950 border border-slate-800 rounded px-2 py-1 text-xs font-mono"
                    />
                  </label>
                  <div className="text-xs text-slate-500">
                    Save writes to `runtime/config.yaml` with archive backup and audit JSONL. It also forces live trading off and may restart the runner.
                  </div>
                </div>

                {saveResult && (
                  <pre className="text-xs font-mono whitespace-pre-wrap p-3 rounded-lg border border-slate-800 bg-slate-950/40">
                    {JSON.stringify(saveResult, null, 2)}
                  </pre>
                )}
              </div>
            </div>
          )}

          {tab === "commandPack" && (
            <div className="space-y-4">
              <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/30">
                <div className="text-xs uppercase tracking-wider text-slate-400 mb-3">Command Pack</div>
                {commandPackData?.ok === false ? (
                  <div className="text-sm text-slate-300">
                    Missing command pack asset. error:{" "}
                    <span className="font-mono">{commandPackData.error || "unknown"}</span>
                    <div className="text-xs text-slate-500 font-mono mt-2">{commandPackData.path}</div>
                  </div>
                ) : (
                  <>
                    <textarea
                      readOnly
                      value={safeGet(commandPackData, "text", "")}
                      className="w-full h-[70vh] bg-slate-950 border border-slate-800 rounded p-3 text-xs font-mono text-slate-100"
                    />
                    <button
                      onClick={async () => {
                        const text = safeGet(commandPackData, "text", "");
                        try {
                          await navigator.clipboard.writeText(text);
                        } catch {
                          // ignore
                        }
                      }}
                      className="inline-flex items-center gap-2 px-3 py-2 rounded-lg border border-slate-800 bg-slate-900/40 text-sm font-bold"
                    >
                      Copy
                    </button>
                  </>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
