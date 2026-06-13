import React, { useState, useEffect } from 'react';
import { 
  Activity, 
  Shield, 
  Server,
  Target,
  DollarSign,
  BookOpen,
  Settings,
  Zap,
  Pause,
  Lock,
  Newspaper,
  TrendingUp,
  AlertTriangle,
  Clock,
  CheckCircle,
  XCircle
} from 'lucide-react';
import { apiGet } from './api/client';
import BiasStatePanel from './components/BiasStatePanel';

// --- CONSTANTS ---
const MISSING = "MISSING";
const STALE = "STALE";
const NO_NEWS_INGESTED = "NO_NEWS_INGESTED";

// Helper: Check if data is stale
const isStale = (truthEnvelope, maxAgeMs = 120000) => {
  if (!truthEnvelope || !truthEnvelope.truth) return true;
  const freshness = truthEnvelope.truth.freshness_ms;
  if (freshness === null || freshness === undefined) return true;
  return freshness > maxAgeMs;
};

// Helper: Get field value or MISSING
const getField = (obj, path, defaultValue = MISSING) => {
  if (!obj) return defaultValue;
  const keys = path.split('.');
  let current = obj;
  for (const key of keys) {
    if (current === null || current === undefined) return defaultValue;
    current = current[key];
  }
  return current === null || current === undefined ? defaultValue : current;
};

// --- STYLES ---
const cardStyle = {
  background: 'rgba(20, 22, 26, 0.8)',
  border: '1px solid #2d2e35',
  borderRadius: '8px',
  padding: '24px',
  backdropFilter: 'blur(10px)',
  WebkitBackdropFilter: 'blur(10px)'
};

const tableHeaderStyle = {
  textAlign: 'left',
  padding: '12px 16px',
  color: '#9ca3af',
  fontSize: '12px',
  fontWeight: '600',
  textTransform: 'uppercase',
  letterSpacing: '0.05em',
  borderBottom: '1px solid #2d2e35'
};

const tableCellStyle = {
  padding: '16px',
  borderBottom: '1px solid #2d2e35',
  color: '#e5e7eb',
  fontSize: '14px'
};

// --- COMPONENT: ACCOUNTS TAB ---
const AccountsTab = ({ accounts }) => {
  if (!accounts || !accounts.data || !accounts.data.accounts) {
    return (
      <div className="glass-card" style={cardStyle}>
        <div style={{ textAlign: 'center', padding: '40px', color: '#9ca3af' }}>
          <DollarSign size={48} style={{ margin: '0 auto 16px', opacity: 0.5 }} />
          <h3>No Account Data Available</h3>
        </div>
      </div>
    );
  }

  return (
    <div className="glass-card" style={{ ...cardStyle, padding: 0, overflow: 'hidden' }}>
      <div style={{ padding: '24px', borderBottom: '1px solid #2d2e35', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h3 style={{ fontSize: '18px', fontWeight: 'bold', color: '#ffffff', margin: 0 }}>Active Accounts</h3>
        <span style={{ fontSize: '12px', color: '#9ca3af', background: 'rgba(255,255,255,0.1)', padding: '4px 8px', borderRadius: '4px' }}>
          {accounts.data.accounts.length} Connected
        </span>
      </div>
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr>
              <th style={tableHeaderStyle}>Account ID</th>
              <th style={tableHeaderStyle}>Strategy</th>
              <th style={tableHeaderStyle}>Balance</th>
              <th style={tableHeaderStyle}>Equity</th>
              <th style={tableHeaderStyle}>Margin Used</th>
              <th style={tableHeaderStyle}>Open Trades</th>
              <th style={tableHeaderStyle}>Status</th>
            </tr>
          </thead>
          <tbody>
            {accounts.data.accounts.map((acc, idx) => (
              <tr key={idx} style={{ background: idx % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.02)' }}>
                <td style={{ ...tableCellStyle, fontFamily: 'monospace' }}>{acc.id_masked || acc.account_id_masked || MISSING}</td>
                <td style={tableCellStyle}>
                  <span style={{ color: '#60a5fa', background: 'rgba(96, 165, 250, 0.1)', padding: '4px 8px', borderRadius: '4px', fontSize: '12px' }}>
                    {acc.strategy || 'None'}
                  </span>
                </td>
                <td style={{ ...tableCellStyle, fontWeight: 'bold', color: '#4ade80' }}>
                  {acc.currency} {acc.balance?.toFixed(2)}
                </td>
                <td style={tableCellStyle}>{acc.currency} {acc.equity?.toFixed(2)}</td>
                <td style={tableCellStyle}>{acc.currency} {acc.margin_used?.toFixed(2)}</td>
                <td style={tableCellStyle}>{acc.open_trades_count || 0}</td>
                <td style={tableCellStyle}>
                  {acc.execution_capable ? (
                    <span style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#4ade80' }}>
                      <CheckCircle size={14} /> Active
                    </span>
                  ) : (
                    <span style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#9ca3af' }}>
                      <XCircle size={14} /> Inactive
                    </span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

// --- COMPONENT: JOURNAL TAB (Signals) ---
const JournalTab = ({ signals }) => {
  if (!signals || !signals.data || !signals.data.signals) {
    return (
      <div className="glass-card" style={cardStyle}>
        <div style={{ textAlign: 'center', padding: '40px', color: '#9ca3af' }}>
          <BookOpen size={48} style={{ margin: '0 auto 16px', opacity: 0.5 }} />
          <h3>No Journal/Signal Data Available</h3>
        </div>
      </div>
    );
  }

  const signalList = signals.data.signals;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      <div className="glass-card" style={{ ...cardStyle, padding: 0, overflow: 'hidden' }}>
        <div style={{ padding: '24px', borderBottom: '1px solid #2d2e35' }}>
          <h3 style={{ fontSize: '18px', fontWeight: 'bold', color: '#ffffff', margin: 0 }}>Recent Signals</h3>
        </div>
        
        {signalList.length === 0 ? (
          <div style={{ padding: '40px', textAlign: 'center', color: '#9ca3af' }}>
            No recent signals generated. System is scanning...
          </div>
        ) : (
          <div style={{ display: 'grid', gap: '1px', background: '#2d2e35' }}>
            {signalList.map((sig, idx) => (
              <div key={idx} style={{ background: '#14161a', padding: '20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                  <div style={{ 
                    width: '40px', height: '40px', borderRadius: '8px', 
                    background: sig.direction === 'BUY' ? 'rgba(74, 222, 128, 0.1)' : 'rgba(248, 113, 113, 0.1)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    color: sig.direction === 'BUY' ? '#4ade80' : '#f87171'
                  }}>
                    {sig.direction === 'BUY' ? <TrendingUp size={20} /> : <TrendingUp size={20} style={{ transform: 'scaleY(-1)' }} />}
                  </div>
                  <div>
                    <div style={{ fontWeight: 'bold', color: '#fff', fontSize: '16px' }}>{sig.instrument}</div>
                    <div style={{ color: '#9ca3af', fontSize: '12px' }}>{new Date(sig.timestamp).toLocaleString()}</div>
                  </div>
                </div>
                
                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontWeight: 'bold', color: '#fff', fontSize: '16px' }}>{sig.price}</div>
                  <div style={{ color: '#60a5fa', fontSize: '12px' }}>{sig.strategy}</div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

// --- COMPONENT: INTELLIGENCE TAB (News) ---
const IntelligenceTab = ({ news }) => {
  if (!news || !news.data || !news.data.news) {
    return (
      <div className="glass-card" style={cardStyle}>
        <div style={{ textAlign: 'center', padding: '40px', color: '#9ca3af' }}>
          <Target size={48} style={{ margin: '0 auto 16px', opacity: 0.5 }} />
          <h3>No Intelligence Data Available</h3>
        </div>
      </div>
    );
  }

  return (
    <div className="glass-card" style={{ ...cardStyle, padding: 0, overflow: 'hidden' }}>
      <div style={{ padding: '24px', borderBottom: '1px solid #2d2e35' }}>
        <h3 style={{ fontSize: '18px', fontWeight: 'bold', color: '#ffffff', margin: 0 }}>Market Intelligence</h3>
      </div>
      
      <div style={{ display: 'grid', gap: '1px', background: '#2d2e35' }}>
        {news.data.news.map((item, idx) => (
          <div key={idx} style={{ background: '#14161a', padding: '24px', transition: 'background 0.2s' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
              <span style={{ fontSize: '12px', color: '#60a5fa', background: 'rgba(96, 165, 250, 0.1)', padding: '2px 8px', borderRadius: '4px' }}>
                {item.source || 'Unknown Source'}
              </span>
              <span style={{ fontSize: '12px', color: '#9ca3af', display: 'flex', alignItems: 'center', gap: '4px' }}>
                <Clock size={12} />
                {new Date(item.ts_utc * 1000).toLocaleString()}
              </span>
            </div>
            <h4 style={{ fontSize: '16px', fontWeight: 'bold', color: '#fff', marginBottom: '8px', lineHeight: '1.4' }}>
              {item.title}
            </h4>
            <p style={{ fontSize: '14px', color: '#9ca3af', lineHeight: '1.5', margin: 0 }}>
              {item.summary}
            </p>
            {item.impact && (
              <div style={{ marginTop: '12px', display: 'flex', gap: '8px' }}>
                <span style={{ 
                  fontSize: '11px', fontWeight: 'bold', padding: '2px 8px', borderRadius: '4px', textTransform: 'uppercase',
                  background: item.impact === 'high' ? 'rgba(239, 68, 68, 0.2)' : 'rgba(251, 191, 36, 0.2)',
                  color: item.impact === 'high' ? '#f87171' : '#fbbf24'
                }}>
                  {item.impact} Impact
                </span>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

// --- COMPONENT: SETTINGS TAB ---
const SettingsTab = ({ status }) => {
  if (!status || !status.data) return null;
  const s = status.data;

  const SettingRow = ({ label, value, type = 'text' }) => (
    <div style={{ display: 'flex', justifyContent: 'space-between', padding: '16px 0', borderBottom: '1px solid #2d2e35' }}>
      <span style={{ color: '#9ca3af' }}>{label}</span>
      <span style={{ color: '#fff', fontWeight: '500' }}>
        {type === 'bool' ? (
          value ? <span style={{ color: '#4ade80' }}>Enabled</span> : <span style={{ color: '#f87171' }}>Disabled</span>
        ) : value}
      </span>
    </div>
  );

  return (
    <div className="responsive-grid">
      <div className="glass-card" style={cardStyle}>
        <div style={{ paddingBottom: '16px', borderBottom: '1px solid #2d2e35', marginBottom: '16px' }}>
          <h3 style={{ fontSize: '18px', fontWeight: 'bold', color: '#ffffff', margin: 0 }}>System Configuration</h3>
        </div>
        <SettingRow label="Execution Mode" value={s.mode.toUpperCase()} />
        <SettingRow label="Execution Enabled" value={s.execution_enabled} type="bool" />
        <SettingRow label="Active Strategy" value={s.active_strategy_key} />
        <SettingRow label="Accounts Loaded" value={s.accounts_loaded} />
        <SettingRow label="System Label" value={s.system_label} />
      </div>

      <div className="glass-card" style={cardStyle}>
        <div style={{ paddingBottom: '16px', borderBottom: '1px solid #2d2e35', marginBottom: '16px' }}>
          <h3 style={{ fontSize: '18px', fontWeight: 'bold', color: '#ffffff', margin: 0 }}>Guard Status</h3>
        </div>
        <div style={{ padding: '20px', background: s.execution_guard.allowed ? 'rgba(74, 222, 128, 0.1)' : 'rgba(239, 68, 68, 0.1)', borderRadius: '8px', border: s.execution_guard.allowed ? '1px solid #4ade80' : '1px solid #ef4444' }}>
          <div style={{ fontSize: '14px', fontWeight: 'bold', color: s.execution_guard.allowed ? '#4ade80' : '#f87171', marginBottom: '8px' }}>
            {s.execution_guard.allowed ? 'TRADING ALLOWED' : 'TRADING BLOCKED'}
          </div>
          <div style={{ fontSize: '12px', color: '#e5e7eb' }}>
            Reason: {s.execution_guard.reason_code}
          </div>
        </div>
      </div>
    </div>
  );
};

// --- MISSION CONTROL TAB (Main Dashboard) ---
const MissionControlTab = ({ status, session, accounts, market }) => {
  const currentTime = new Date().toISOString().replace('T', ' ').substring(0, 19) + ' GMT UTC';
  const embargoActive = getField(session?.data, 'block_details.is_embargo', false);
  
  const statusCardStyle = {
    background: 'rgba(0, 0, 0, 0.3)',
    borderRadius: '8px',
    padding: '16px',
    border: '1px solid rgba(34, 197, 94, 0.2)'
  };

  return (
    <div className="responsive-grid">
      {/* LEFT COLUMN */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
        {/* System Status Panel */}
        <div className="glass-card" style={cardStyle}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Server size={20} style={{ color: '#60a5fa' }} />
              <h3 style={{ fontSize: '18px', fontWeight: 'bold', color: '#ffffff', margin: 0 }}>System Status</h3>
            </div>
            <span style={{ fontSize: '12px', color: '#9ca3af', fontFamily: 'monospace' }}>{currentTime}</span>
          </div>
          
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '12px' }}>
            {['CONTROL PLANE', 'RUNNER', 'MARKET DATA', 'OUTLOOK ENGINE'].map((name) => (
              <div key={name} style={statusCardStyle}>
                <div style={{ fontSize: '12px', color: '#9ca3af', marginBottom: '4px' }}>{name}</div>
                <div style={{ color: '#4ade80', fontWeight: 'bold' }}>UP</div>
              </div>
            ))}
          </div>
        </div>

        {/* Quick Account Summary Panel */}
        <div className="glass-card" style={cardStyle}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <DollarSign size={20} style={{ color: '#60a5fa' }} />
              <h3 style={{ fontSize: '18px', fontWeight: 'bold', color: '#ffffff', margin: 0 }}>Quick Account Summary</h3>
            </div>
            <span style={{ fontSize: '12px', color: '#9ca3af', fontFamily: 'monospace' }}>{currentTime}</span>
          </div>
          
          {!accounts || !accounts.data || !accounts.data.accounts || accounts.data.accounts.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '32px 0', color: '#9ca3af' }}>
              <div style={{ color: '#f87171', fontWeight: 'bold', marginBottom: '8px' }}>{MISSING}</div>
              <div style={{ fontSize: '14px' }}>No account data available</div>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {accounts.data.accounts.slice(0, 3).map((acc, idx) => {
                const balance = acc.balance || 0;
                const isPositive = balance >= 0;
                return (
                  <div key={acc.account_id_masked || acc.id || idx} style={{ background: 'rgba(0, 0, 0, 0.3)', borderRadius: '8px', padding: '16px', border: '1px solid #374151' }}>
                    <div style={{ fontSize: '12px', color: '#9ca3af', marginBottom: '4px' }}>{acc.account_id_masked || acc.id || `Account ${idx + 1}`}</div>
                    <div style={{ fontSize: '18px', fontWeight: 'bold', color: isPositive ? '#4ade80' : '#f87171' }}>
                      {acc.currency || '$'} {balance.toFixed(2)}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* RIGHT COLUMN */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
        {/* Session Gate Panel */}
        <div 
          className="glass-card" 
          style={{ 
            ...cardStyle,
            background: embargoActive ? 'rgba(139, 0, 0, 0.3)' : 'rgba(20, 22, 26, 0.8)',
            border: embargoActive ? '3px solid #ff3e3e' : '1px solid #2d2e35',
            borderColor: embargoActive ? '#ff3e3e' : '#2d2e35'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Shield size={20} style={{ color: embargoActive ? '#f87171' : '#60a5fa' }} />
              <h3 style={{ fontSize: '18px', fontWeight: 'bold', color: '#ffffff', margin: 0 }}>Session Gate</h3>
            </div>
            <span style={{ fontSize: '12px', color: '#9ca3af', fontFamily: 'monospace' }}>{currentTime}</span>
          </div>
          
          {!session || !session.data ? (
            <div style={{ textAlign: 'center', padding: '32px 0', color: '#9ca3af' }}>
              <div style={{ color: '#f87171', fontWeight: 'bold', marginBottom: '8px' }}>{MISSING}</div>
              <div style={{ fontSize: '14px' }}>No session data available</div>
            </div>
          ) : (
            <div style={{ textAlign: 'center' }}>
              {embargoActive || getField(session.data, 'readiness') === 'BLOCKED' ? (
                <>
                  <Lock size={48} style={{ color: '#f87171', margin: '0 auto 16px' }} />
                  <div style={{ fontSize: '36px', fontWeight: '900', color: '#f87171', marginBottom: '16px' }}>BLOCKED</div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', alignItems: 'center' }}>
                    {embargoActive && (
                      <div style={{ fontSize: '14px', color: '#fca5a5', background: 'rgba(239, 68, 68, 0.2)', borderRadius: '4px', padding: '4px 12px', display: 'inline-block' }}>news_embargo_active</div>
                    )}
                    {getField(session.data, 'block_details.regime') && (
                      <div style={{ fontSize: '14px', color: '#fca5a5', background: 'rgba(239, 68, 68, 0.2)', borderRadius: '4px', padding: '4px 12px', display: 'inline-block', marginLeft: '8px' }}>
                        {String(getField(session.data, 'block_details.regime')).toLowerCase()}
                      </div>
                    )}
                  </div>
                </>
              ) : (
                <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#4ade80' }}>READY</div>
              )}
            </div>
          )}
        </div>

        {/* Bias Observability Panel */}
        <BiasStatePanel />
      </div>
    </div>
  );
};

// --- MAIN DASHBOARD ---
export default function Dashboard() {
  const [activeTab, setActiveTab] = useState("mission");
  const [data, setData] = useState({
    status: null,
    session: null,
    accounts: null,
    market: null,
    signals: null,
    news: null,
    lastUpdate: null
  });
  const [error, setError] = useState(null);

  const fetchData = async () => {
    try {
      const [status, session, accounts, market, signals, news] = await Promise.all([
        apiGet('/api/status'),
        apiGet('/api/session-regime-gate/snapshot'),
        apiGet('/api/accounts'),
        apiGet('/api/market/overview'),
        apiGet('/api/signals/pending'),
        apiGet('/api/news')
      ]);

      const safeStatus = (status && status.truth && status.truth.complete && status.data) ? status : null;
      const safeSession = (session && session.truth && session.truth.complete && session.data) ? session : null;
      const safeAccounts = (accounts && accounts.truth && accounts.truth.complete && accounts.data) ? accounts : null;
      const safeMarket = (market && market.truth && market.truth.complete && market.data) ? market : null;
      const safeSignals = (signals && signals.truth && signals.truth.complete && signals.data) ? signals : null;
      const safeNews = (news && news.truth && news.truth.complete && news.data) ? news : null;

      setData({
        status: safeStatus,
        session: safeSession,
        accounts: safeAccounts,
        market: safeMarket,
        signals: safeSignals,
        news: safeNews,
        lastUpdate: new Date()
      });
      
      if (!safeStatus && !safeSession && !safeAccounts && !safeMarket && !safeSignals && !safeNews) {
        setError("All backend endpoints failed - no data available");
      } else {
        setError(null);
      }
    } catch (err) {
      console.error("Dashboard Sync Error:", err);
      setError(err.message);
      setData({});
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, []);

  const currentTime = new Date().toISOString().replace('T', ' ').substring(0, 19) + ' GMT UTC';
  const embargoActive = getField(data.session?.data, 'block_details.is_embargo', false);
  const executionEnabled = getField(data.status?.data, 'execution_enabled', false);

  const tabs = [
    { id: "mission", label: "Mission Control", icon: Activity },
    { id: "accounts", label: "Accounts", icon: DollarSign },
    { id: "journal", label: "Journal", icon: BookOpen },
    { id: "intelligence", label: "Intelligence", icon: Target },
    { id: "settings", label: "Settings", icon: Settings },
  ];

  const headerStyle = {
    height: '80px',
    borderBottom: '1px solid #2d2e35',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '0 32px',
    background: 'rgba(20, 22, 26, 0.95)',
    backdropFilter: 'blur(10px)',
    WebkitBackdropFilter: 'blur(10px)'
  };

  const navStyle = {
    height: '56px',
    borderBottom: '1px solid #2d2e35',
    display: 'flex',
    alignItems: 'center',
    padding: '0 32px',
    background: 'rgba(0, 0, 0, 0.2)'
  };

  return (
    <div style={{ minHeight: '100vh', background: 'linear-gradient(135deg, #0a0b0d 0%, #1a1b1f 100%)', color: '#e6e6e6', fontFamily: "'Inter', sans-serif" }}>
      {/* HEADER */}
      <header style={headerStyle}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          {/* Waveform Logo */}
          <div style={{ width: '40px', height: '40px', background: '#3b82f6', borderRadius: '8px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Activity size={24} style={{ color: '#ffffff' }} />
          </div>
          <div>
            <h1 style={{ fontSize: '24px', fontWeight: 'bold', color: '#ffffff', margin: 0 }}>
              FXG <span style={{ fontWeight: '800' }}>AI TRADING</span>
            </h1>
            <div style={{ fontSize: '12px', color: '#9ca3af', marginTop: '2px' }}>PAPER (SAFE MODE)</div>
          </div>
        </div>
        
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          {embargoActive && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '8px 16px', borderRadius: '9999px', border: '2px solid #ef4444', background: 'rgba(239, 68, 68, 0.1)' }}>
              <Pause size={16} style={{ color: '#f87171' }} />
              <span style={{ color: '#f87171', fontWeight: 'bold', fontSize: '14px' }}>EMBARGO ACTIVE</span>
            </div>
          )}
          {!executionEnabled && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '8px 16px', borderRadius: '9999px', border: '2px solid #ef4444', background: 'rgba(239, 68, 68, 0.1)' }}>
              <Zap size={16} style={{ color: '#f87171' }} />
              <span style={{ color: '#f87171', fontWeight: 'bold', fontSize: '14px' }}>TRADES OFF</span>
            </div>
          )}
          <div style={{ fontSize: '14px', color: '#9ca3af', fontFamily: 'monospace' }}>{currentTime}</div>
        </div>
      </header>

      {/* NAVIGATION BAR */}
      <nav style={navStyle}>
        <div style={{ display: 'flex', gap: '4px' }}>
          {tabs.map(tab => {
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  padding: '12px 24px',
                  borderTopLeftRadius: '8px',
                  borderTopRightRadius: '8px',
                  border: 'none',
                  background: isActive ? '#14161a' : 'transparent',
                  color: isActive ? '#60a5fa' : '#9ca3af',
                  borderTop: isActive ? '2px solid #60a5fa' : '2px solid transparent',
                  cursor: 'pointer',
                  transition: 'all 0.2s',
                  fontWeight: '600',
                  fontSize: '14px'
                }}
                onMouseEnter={(e) => {
                  if (!isActive) {
                    e.target.style.color = '#ffffff';
                    e.target.style.background = '#1a1c22';
                  }
                }}
                onMouseLeave={(e) => {
                  if (!isActive) {
                    e.target.style.color = '#9ca3af';
                    e.target.style.background = 'transparent';
                  }
                }}
              >
                <tab.icon size={18} />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>
      </nav>

      {/* MAIN CONTENT */}
      <main style={{ padding: '32px' }}>
        <div style={{ maxWidth: '1280px', margin: '0 auto' }}>
          {activeTab === 'mission' && <MissionControlTab status={data.status} session={data.session} accounts={data.accounts} market={data.market} />}
          {activeTab === 'accounts' && <AccountsTab accounts={data.accounts} />}
          {activeTab === 'journal' && <JournalTab signals={data.signals} />}
          {activeTab === 'intelligence' && <IntelligenceTab news={data.news} />}
          {activeTab === 'settings' && <SettingsTab status={data.status} />}
        </div>
      </main>
    </div>
  );
}
