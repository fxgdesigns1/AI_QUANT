import React, { useState, useEffect } from 'react'

const API = '/api'

function useFetch(url, deps = []) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  useEffect(() => {
    setLoading(true)
    fetch(url)
      .then(r => r.json())
      .then(setData)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, deps)
  return { data, loading, error }
}

function Tab({ active, onClick, children }) {
  return (
    <button
      onClick={onClick}
      style={{
        padding: '8px 16px',
        border: 'none',
        background: active ? '#27272a' : 'transparent',
        color: active ? '#fff' : '#a1a1aa',
        cursor: 'pointer',
        borderRadius: 6,
        fontWeight: active ? 600 : 400,
      }}
    >
      {children}
    </button>
  )
}

function Overview({ state }) {
  if (!state) return <p>Loading...</p>
  const health = state.health || 'unknown'
  const masterFeed = state.master_feed || {}
  const oandaId = masterFeed.oanda_account_id || '010'
  const lastSignal = state.last_50_signals?.[0]
  const counts = state.ftmo_rules_counts || {}
  const routing = state.routing_rules || {}
  return (
    <div style={{ padding: 24 }}>
      <h2 style={{ marginTop: 0 }}>Overview</h2>
      <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap', marginBottom: 24 }}>
        <div style={{ background: '#18181b', padding: 16, borderRadius: 8, minWidth: 200 }}>
          <div style={{ color: '#71717a', fontSize: 12, marginBottom: 4 }}>Connection</div>
          <div style={{ fontSize: 18, fontWeight: 600 }}>
            {health === 'connected' ? 'Connected ✅' : 'Disconnected'}
          </div>
        </div>
        <div style={{ background: '#18181b', padding: 16, borderRadius: 8, minWidth: 200 }}>
          <div style={{ color: '#71717a', fontSize: 12, marginBottom: 4 }}>Master feed (OANDA)</div>
          <div style={{ fontSize: 18 }}>Account {oandaId}</div>
        </div>
        <div style={{ background: '#18181b', padding: 16, borderRadius: 8, minWidth: 200 }}>
          <div style={{ color: '#71717a', fontSize: 12, marginBottom: 4 }}>Fanout</div>
          <div style={{ fontSize: 18 }}>{routing.fanout_enabled ? 'On' : 'Off'}</div>
        </div>
        <div style={{ background: '#18181b', padding: 16, borderRadius: 8, minWidth: 200 }}>
          <div style={{ color: '#71717a', fontSize: 12, marginBottom: 4 }}>Last signal</div>
          <div style={{ fontSize: 14, fontFamily: 'monospace' }}>
            {lastSignal?.id ? lastSignal.id.slice(0, 8) + '...' : '—'}
          </div>
        </div>
        <div style={{ background: '#18181b', padding: 16, borderRadius: 8, minWidth: 200 }}>
          <div style={{ color: '#71717a', fontSize: 12, marginBottom: 4 }}>ACCEPTED_DRY_RUN</div>
          <div style={{ fontSize: 18 }}>{counts.accepted_dry_run ?? 0}</div>
        </div>
        <div style={{ background: '#18181b', padding: 16, borderRadius: 8, minWidth: 200 }}>
          <div style={{ color: '#71717a', fontSize: 12, marginBottom: 4 }}>REJECTED</div>
          <div style={{ fontSize: 18 }}>{counts.rejected ?? 0}</div>
        </div>
      </div>
      <h3>Accounts (enabled + connected)</h3>
      <ul style={{ margin: 0, paddingLeft: 20 }}>
        {(state.accounts || [])
          .filter(a => a.enabled)
          .map(a => (
            <li key={a.id}>
              {a.label || a.id}
              {a.connected ? ' ✅' : ' (no recent signal)'}
            </li>
          ))}
        {(!state.accounts || state.accounts.filter(a => a.enabled).length === 0) && (
          <li style={{ color: '#71717a' }}>None</li>
        )}
      </ul>
    </div>
  )
}

function Accounts({ accounts, state, onRefresh }) {
  const [updating, setUpdating] = useState(null)
  const [secretRef, setSecretRef] = useState('')
  const [secretValue, setSecretValue] = useState('')
  const [secretSending, setSecretSending] = useState(false)
  const [masterFeedId, setMasterFeedId] = useState('010')
  const [masterFeedSaving, setMasterFeedSaving] = useState(false)
  useEffect(() => {
    const id = state?.master_feed?.oanda_account_id
    if (id) setMasterFeedId(id)
  }, [state?.master_feed?.oanda_account_id])

  const toggle = async (accountId, enabled) => {
    setUpdating(accountId)
    try {
      await fetch(`${API}/accounts/enable`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: accountId, enabled }),
      })
      onRefresh()
    } finally {
      setUpdating(null)
    }
  }

  const saveMasterFeed = async () => {
    setMasterFeedSaving(true)
    try {
      await fetch(`${API}/master_feed`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ oanda_account_id: masterFeedId }),
      })
      onRefresh()
    } finally {
      setMasterFeedSaving(false)
    }
  }

  const setSecret = async () => {
    if (!secretRef || !secretValue) return
    setSecretSending(true)
    try {
      const r = await fetch(`${API}/secrets`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ref: secretRef, value: secretValue }),
      })
      if (r.ok) {
        setSecretValue('')
        setSecretRef('')
      } else {
        const j = await r.json().catch(() => ({}))
        alert(j.detail || 'Failed')
      }
    } finally {
      setSecretSending(false)
    }
  }

  const list = accounts?.accounts || []
  const accStateById = (state?.accounts || []).reduce((m, x) => { m[x.id] = x; return m }, {})
  return (
    <div style={{ padding: 24 }}>
      <h2 style={{ marginTop: 0 }}>Accounts</h2>
      <h3 style={{ marginTop: 24, marginBottom: 12 }}>Master feed (OANDA)</h3>
      <p style={{ color: '#71717a', fontSize: 14, marginBottom: 8 }}>
        OANDA account ID that generates signals (default: 010)
      </p>
      <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 24 }}>
        <input
          value={masterFeedId}
          onChange={e => setMasterFeedId(e.target.value)}
          placeholder="010"
          style={{
            padding: 8,
            width: 120,
            background: '#27272a',
            border: '1px solid #3f3f46',
            borderRadius: 6,
            color: '#fff',
          }}
        />
        <button
          onClick={saveMasterFeed}
          disabled={masterFeedSaving}
          style={{
            padding: '8px 16px',
            background: '#3b82f6',
            color: '#fff',
            border: 'none',
            borderRadius: 6,
            cursor: 'pointer',
          }}
        >
          {masterFeedSaving ? 'Saving...' : 'Save'}
        </button>
      </div>
      <h3 style={{ marginTop: 24, marginBottom: 12 }}>Prop accounts</h3>
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr style={{ borderBottom: '1px solid #27272a' }}>
            <th style={{ textAlign: 'left', padding: 12 }}>ID</th>
            <th style={{ textAlign: 'left', padding: 12 }}>Label</th>
            <th style={{ textAlign: 'left', padding: 12 }}>Environment</th>
            <th style={{ textAlign: 'left', padding: 12 }}>Connected</th>
            <th style={{ textAlign: 'left', padding: 12 }}>Status</th>
            <th style={{ textAlign: 'left', padding: 12 }}>Actions</th>
          </tr>
        </thead>
        <tbody>
          {list.map(a => {
            const aid = a.id || a.account_id
            const accState = accStateById[aid]
            return (
              <tr key={aid} style={{ borderBottom: '1px solid #27272a' }}>
                <td style={{ padding: 12 }}>{aid}</td>
                <td style={{ padding: 12 }}>{a.label || '—'}</td>
                <td style={{ padding: 12 }}>{a.environment || '—'}</td>
                <td style={{ padding: 12 }}>{accState?.connected ? '✅' : '—'}</td>
                <td style={{ padding: 12 }}>{a.enabled ? 'Enabled' : 'Disabled'}</td>
                <td style={{ padding: 12 }}>
                  <button
                    onClick={() => toggle(aid, !a.enabled)}
                    disabled={updating === aid}
                    style={{
                      padding: '6px 12px',
                      background: a.enabled ? '#dc2626' : '#22c55e',
                      color: '#fff',
                      border: 'none',
                      borderRadius: 6,
                      cursor: 'pointer',
                    }}
                  >
                    {a.enabled ? 'Disable' : 'Enable'}
                  </button>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
      <h3 style={{ marginTop: 32 }}>Set credential</h3>
      <p style={{ color: '#71717a', fontSize: 14 }}>
        Ref format: ftmo_demo_01/login or keychain:fxg/mt5/ftmo_demo_01/login
      </p>
      <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
        <input
          placeholder="Ref (e.g. ftmo_demo_01/login)"
          value={secretRef}
          onChange={e => setSecretRef(e.target.value)}
          style={{
            padding: 8,
            width: 280,
            background: '#27272a',
            border: '1px solid #3f3f46',
            borderRadius: 6,
            color: '#fff',
          }}
        />
        <input
          type="password"
          placeholder="Value (never stored in browser)"
          value={secretValue}
          onChange={e => setSecretValue(e.target.value)}
          style={{
            padding: 8,
            width: 200,
            background: '#27272a',
            border: '1px solid #3f3f46',
            borderRadius: 6,
            color: '#fff',
          }}
        />
        <button
          onClick={setSecret}
          disabled={secretSending || !secretRef || !secretValue}
          style={{
            padding: '8px 16px',
            background: '#3b82f6',
            color: '#fff',
            border: 'none',
            borderRadius: 6,
            cursor: 'pointer',
          }}
        >
          Set
        </button>
      </div>
    </div>
  )
}

function Signals({ state }) {
  const bridgeSignals = state?.last_50_signals || []
  const emittedSignals = state?.last_100_emitted_signals || []
  const sigFile = state?.signals_file
  return (
    <div style={{ padding: 24 }}>
      <h2 style={{ marginTop: 0 }}>Signals</h2>
      <p style={{ color: '#71717a', marginBottom: 16 }}>
        Emitted (signals.jsonl) and bridge decisions (ftmo_bridge_log.jsonl)
      </p>
      <h3>Emitted signals (last 100)</h3>
      <div style={{ overflowX: 'auto', marginBottom: 32 }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
          <thead>
            <tr style={{ borderBottom: '1px solid #27272a' }}>
              <th style={{ textAlign: 'left', padding: 8 }}>Time</th>
              <th style={{ textAlign: 'left', padding: 8 }}>ID</th>
              <th style={{ textAlign: 'left', padding: 8 }}>Symbol</th>
              <th style={{ textAlign: 'left', padding: 8 }}>Side</th>
              <th style={{ textAlign: 'left', padding: 8 }}>Bridge Account</th>
            </tr>
          </thead>
          <tbody>
            {emittedSignals.slice(0, 100).map((s, i) => (
              <tr key={i} style={{ borderBottom: '1px solid #27272a' }}>
                <td style={{ padding: 8 }}>{s.timestamp_utc || '—'}</td>
                <td style={{ padding: 8, fontFamily: 'monospace', fontSize: 11 }}>
                  {s.signal_id ? s.signal_id.slice(0, 12) + '...' : '—'}
                </td>
                <td style={{ padding: 8 }}>{s.symbol || '—'}</td>
                <td style={{ padding: 8 }}>{s.side || '—'}</td>
                <td style={{ padding: 8 }}>{s.bridge_account || '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <h3>Bridge decisions (last 50)</h3>
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
          <thead>
            <tr style={{ borderBottom: '1px solid #27272a' }}>
              <th style={{ textAlign: 'left', padding: 8 }}>Time</th>
              <th style={{ textAlign: 'left', padding: 8 }}>ID</th>
              <th style={{ textAlign: 'left', padding: 8 }}>Message</th>
            </tr>
          </thead>
          <tbody>
            {bridgeSignals.map((s, i) => (
              <tr key={i} style={{ borderBottom: '1px solid #27272a' }}>
                <td style={{ padding: 8 }}>{s.ts || '—'}</td>
                <td style={{ padding: 8, fontFamily: 'monospace', fontSize: 11 }}>
                  {s.id ? s.id.slice(0, 12) + '...' : '—'}
                </td>
                <td style={{ padding: 8 }}>{s.msg || s.message || '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function LogsHealth({ state, onVerify }) {
  const [verifying, setVerifying] = useState(false)
  const [verifyResult, setVerifyResult] = useState(null)
  const sigFile = state?.signals_file || {}
  const logFile = state?.log_file || {}

  const runVerify = async () => {
    setVerifying(true)
    setVerifyResult(null)
    try {
      const r = await fetch(`${API}/bridge/verify?bridge_account=ftmo_demo_01&timeout=90`, {
        method: 'POST',
      })
      const j = await r.json()
      setVerifyResult(j)
    } finally {
      setVerifying(false)
    }
  }

  return (
    <div style={{ padding: 24 }}>
      <h2 style={{ marginTop: 0 }}>Logs & Health</h2>
      <h3>File status</h3>
      <table style={{ borderCollapse: 'collapse', marginBottom: 24 }}>
        <tbody>
          <tr style={{ borderBottom: '1px solid #27272a' }}>
            <td style={{ padding: 8, color: '#71717a' }}>signals.jsonl</td>
            <td style={{ padding: 8 }}>{sigFile.realpath || sigFile.path || '—'}</td>
            <td style={{ padding: 8 }}>mtime: {sigFile.mtime ? new Date(sigFile.mtime * 1000).toISOString() : '—'}</td>
            <td style={{ padding: 8 }}>size: {sigFile.size ?? '—'} bytes</td>
          </tr>
          <tr style={{ borderBottom: '1px solid #27272a' }}>
            <td style={{ padding: 8, color: '#71717a' }}>ftmo_bridge_log.jsonl</td>
            <td style={{ padding: 8 }}>{logFile.realpath || logFile.path || '—'}</td>
            <td style={{ padding: 8 }}>mtime: {logFile.mtime ? new Date(logFile.mtime * 1000).toISOString() : '—'}</td>
            <td style={{ padding: 8 }}>size: {logFile.size ?? '—'} bytes</td>
          </tr>
        </tbody>
      </table>
      <h3>Run verification</h3>
      <button
        onClick={runVerify}
        disabled={verifying}
        style={{
          padding: '10px 20px',
          background: '#3b82f6',
          color: '#fff',
          border: 'none',
          borderRadius: 6,
          cursor: 'pointer',
        }}
      >
        {verifying ? 'Running...' : 'Run Verification'}
      </button>
      {verifyResult && (
        <pre
          style={{
            marginTop: 16,
            padding: 16,
            background: '#18181b',
            borderRadius: 8,
            overflow: 'auto',
            fontSize: 12,
            whiteSpace: 'pre-wrap',
          }}
        >
          {verifyResult.ok ? '✅ ' : '❌ '}
          {verifyResult.output}
        </pre>
      )}
    </div>
  )
}

export default function App() {
  const [tab, setTab] = useState('overview')
  const { data: state, loading, error, refetch: refetchState } = useFetch(`${API}/bridge/state`, [tab])
  const { data: accounts, refetch: refetchAccounts } = useFetch(`${API}/accounts`, [tab])

  const refresh = () => {
    refetchState()
    refetchAccounts()
  }

  return (
    <div>
      <header
        style={{
          padding: '16px 24px',
          borderBottom: '1px solid #27272a',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        <h1 style={{ margin: 0, fontSize: 20 }}>Bridge Dashboard</h1>
        <div style={{ display: 'flex', gap: 8 }}>
          <Tab active={tab === 'overview'} onClick={() => setTab('overview')}>
            Overview
          </Tab>
          <Tab active={tab === 'accounts'} onClick={() => setTab('accounts')}>
            Accounts
          </Tab>
          <Tab active={tab === 'signals'} onClick={() => setTab('signals')}>
            Signals
          </Tab>
          <Tab active={tab === 'logs'} onClick={() => setTab('logs')}>
            Logs/Health
          </Tab>
        </div>
      </header>
      {loading && tab === 'overview' && <p style={{ padding: 24 }}>Loading...</p>}
      {error && <p style={{ padding: 24, color: '#ef4444' }}>Error: {error}</p>}
      {tab === 'overview' && <Overview state={state} />}
      {tab === 'accounts' && <Accounts accounts={accounts} state={state} onRefresh={refresh} />}
      {tab === 'signals' && <Signals state={state} />}
      {tab === 'logs' && <LogsHealth state={state} onVerify={refresh} />}
    </div>
  )
}
