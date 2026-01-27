/**
 * Local Trade Dashboard - Authoritative OANDA /trades Version
 * Mirroring VM Trade Journal UX
 * 
 * TRUTH SOURCE:
 * - OANDA /v3/accounts/{id}/trades (via /api/trades)
 * 
 * LAYOUT:
 * - Header: Title + Source Badge
 * - Summary Bar: Global KPIs
 * - Controls: Account (Left) | Instrument (Right)
 * - Table: Detailed Trade Journal
 */

import { useState, useEffect } from 'react';

const API_BASE = '/api';

// --- Components ---

const SummaryMetric = ({ label, value, subtext, color = 'text-gray-900' }) => (
  <div className="bg-white p-4 rounded-lg border border-gray-200 shadow-sm flex flex-col">
    <span className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-1">{label}</span>
    <span className={`text-2xl font-bold ${color}`}>{value}</span>
    {subtext && <span className="text-xs text-gray-400 mt-1">{subtext}</span>}
  </div>
);

const Badge = ({ children, type = 'neutral' }) => {
  const styles = {
    neutral: 'bg-gray-100 text-gray-600 border-gray-200',
    success: 'bg-green-100 text-green-700 border-green-200',
    error: 'bg-red-100 text-red-700 border-red-200',
    warning: 'bg-amber-100 text-amber-700 border-amber-200',
    info: 'bg-blue-100 text-blue-700 border-blue-200',
  };
  return (
    <span className={`px-2 py-0.5 rounded text-xs font-bold border ${styles[type]} uppercase tracking-wide whitespace-nowrap`}>
      {children}
    </span>
  );
};

// --- Main Component ---

function LocalTradeDashboard() {
  const [trades, setTrades] = useState([]);
  const [stats, setStats] = useState(null);
  const [dataConfidence, setDataConfidence] = useState('HIGH');
  const [dataSource, setDataSource] = useState('unknown');
  const [filters, setFilters] = useState({ account_suffix: '', instrument: '' });
  const [availableFilters, setAvailableFilters] = useState({ accounts: [], instruments: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Initial Load
  useEffect(() => {
    fetchFilters();
  }, []);

  // Reload data on filter change
  useEffect(() => {
    loadData();
  }, [filters]);

  const fetchFilters = async () => {
    try {
      const res = await fetch(`${API_BASE}/filters`);
      const data = await res.json();
      if (data.success) {
        setAvailableFilters(data);
      }
    } catch (err) {
      console.error('Failed to load filters', err);
    }
  };

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      // Build query
      const params = new URLSearchParams();
      if (filters.account_suffix) params.append('account_suffix', filters.account_suffix);
      if (filters.instrument) params.append('instrument', filters.instrument);

      const [tradesRes, statsRes] = await Promise.all([
        fetch(`${API_BASE}/trades?${params.toString()}`),
        fetch(`${API_BASE}/stats`) // Global stats, usually you'd want filtered stats too but endpoint handles global
      ]);

      if (!tradesRes.ok || !statsRes.ok) throw new Error('API Error');

      const tradesData = await tradesRes.json();
      const statsData = await statsRes.json();

      if (tradesData.success) {
        setTrades(tradesData.trades || []);
        setDataSource(tradesData.source || 'unknown');
      }
      if (statsData.success) {
        setStats(statsData.stats);
        setDataConfidence(statsData.data_confidence || 'HIGH');
      }

    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Formatters
  const fmtCurrency = (val) => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(val);
  const fmtDate = (str) => {
    if (!str) return '-';
    return new Date(str).toLocaleString(undefined, { 
      month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', hour12: false 
    });
  };
  const fmtDuration = (secs) => {
    if (!secs) return '-';
    if (secs < 60) return `${secs}s`;
    if (secs < 3600) return `${Math.floor(secs/60)}m`;
    return `${(secs/3600).toFixed(1)}h`;
  };

  // KPI Calculations (Client-side for filtered view)
  const filteredStats = {
    count: trades.length,
    wins: trades.filter(t => t.result === 'WIN').length,
    losses: trades.filter(t => t.result === 'LOSS').length,
    pl: trades.reduce((acc, t) => acc + (t.realized_pl || 0), 0),
  };
  filteredStats.winRate = filteredStats.count > 0 ? (filteredStats.wins / filteredStats.count) * 100 : 0;
  
  // Expectancy approx for filtered view
  const totalWinAmt = trades.filter(t => t.realized_pl > 0).reduce((acc, t) => acc + t.realized_pl, 0);
  const totalLossAmt = trades.filter(t => t.realized_pl < 0).reduce((acc, t) => acc + t.realized_pl, 0);
  const avgWin = filteredStats.wins > 0 ? totalWinAmt / filteredStats.wins : 0;
  const avgLoss = filteredStats.losses > 0 ? totalLossAmt / filteredStats.losses : 0;
  filteredStats.expectancy = (filteredStats.count > 0) ? ((filteredStats.wins/filteredStats.count * avgWin) + (filteredStats.losses/filteredStats.count * avgLoss)) : 0;


  return (
    <div className="min-h-screen bg-slate-50 text-slate-800 font-sans">
      
      {/* Header */}
      <header className="bg-white border-b border-slate-200 px-6 py-4 flex items-center justify-between sticky top-0 z-10 shadow-sm">
        <div className="flex items-center gap-4">
          <h1 className="text-lg font-bold text-slate-900 tracking-tight">OANDA Trade Journal</h1>
          <Badge type="success">SOURCE: OANDA /trades (authoritative)</Badge>
        </div>
        <div className="text-xs text-slate-400 font-mono">
          Last Sync: {new Date().toLocaleTimeString()}
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8">

        {/* Error */}
        {error && (
          <div className="bg-red-50 border-l-4 border-red-500 p-4 mb-6 text-red-700">
            <strong>System Error:</strong> {error}
          </div>
        )}

        {/* Top Summary Bar (Filtered) */}
        <section className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-8">
          <SummaryMetric label="Trades" value={filteredStats.count} />
          <SummaryMetric 
            label="Net P&L" 
            value={fmtCurrency(filteredStats.pl)} 
            color={filteredStats.pl >= 0 ? 'text-emerald-600' : 'text-rose-600'} 
          />
          <SummaryMetric 
            label="Win Rate" 
            value={filteredStats.count > 0 ? `${filteredStats.winRate.toFixed(1)}%` : '-'}
            subtext={`${filteredStats.wins}W - ${filteredStats.losses}L`}
            color={filteredStats.winRate >= 50 ? 'text-emerald-600' : 'text-amber-600'}
          />
           <SummaryMetric 
            label="Expectancy" 
            value={filteredStats.count > 0 ? fmtCurrency(filteredStats.expectancy) : '-'} 
            color={filteredStats.expectancy >= 0 ? 'text-emerald-600' : 'text-rose-600'}
          />
           <SummaryMetric 
            label="Status" 
            value={dataConfidence} 
            color={dataConfidence === 'HIGH' ? 'text-emerald-600' : 'text-rose-600'}
            subtext="Data Confidence"
          />
        </section>

        {/* Controls */}
        <section className="bg-white rounded-lg border border-slate-200 p-4 mb-6 shadow-sm flex flex-col md:flex-row gap-6 items-end">
          <div className="flex-1 w-full">
            <label htmlFor="account-select" className="block text-xs font-bold text-slate-500 uppercase mb-1">Account</label>
            <select 
              id="account-select"
              className="w-full bg-slate-50 border border-slate-300 text-slate-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 p-2.5"
              value={filters.account_suffix}
              onChange={(e) => setFilters(prev => ({ ...prev, account_suffix: e.target.value }))}
            >
              <option value="">ALL ACCOUNTS</option>
              {availableFilters.accounts.map(acc => (
                <option key={acc} value={acc}>Account {acc}</option>
              ))}
            </select>
          </div>
          <div className="flex-1 w-full">
            <label htmlFor="instrument-select" className="block text-xs font-bold text-slate-500 uppercase mb-1">Instrument</label>
            <select 
              id="instrument-select"
              className="w-full bg-slate-50 border border-slate-300 text-slate-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 p-2.5"
              value={filters.instrument}
              onChange={(e) => setFilters(prev => ({ ...prev, instrument: e.target.value }))}
            >
              <option value="">ALL INSTRUMENTS</option>
              {availableFilters.instruments.map(inst => (
                <option key={inst} value={inst}>{inst}</option>
              ))}
            </select>
          </div>
          <div className="pb-1">
             <button 
               onClick={() => setFilters({ account_suffix: '', instrument: '' })}
               className="text-sm text-blue-600 hover:text-blue-800 font-medium"
             >
               Reset Filters
             </button>
          </div>
        </section>

        {/* Trade Table */}
        <section className="bg-white rounded-lg border border-slate-200 shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-left text-slate-600">
              <thead className="text-xs text-slate-500 uppercase bg-slate-50 border-b border-slate-200">
                <tr>
                  <th className="px-6 py-3">Account</th>
                  <th className="px-6 py-3">Instrument</th>
                  <th className="px-6 py-3">Dir</th>
                  <th className="px-6 py-3 text-right">Entry</th>
                  <th className="px-6 py-3 text-right">Exit</th>
                  <th className="px-6 py-3 text-right">P&L</th>
                  <th className="px-6 py-3 text-center">Result</th>
                  <th className="px-6 py-3 text-center">RR</th>
                  <th className="px-6 py-3 text-right">Dur</th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr>
                    <td colSpan="9" className="px-6 py-12 text-center text-slate-400">
                      Loading authoritative data...
                    </td>
                  </tr>
                ) : trades.length === 0 ? (
                  <tr>
                    <td colSpan="9" className="px-6 py-12 text-center">
                       <div className="flex flex-col items-center">
                         <span className="text-2xl mb-2">📭</span>
                         <span className="font-bold text-slate-700">No closed trades returned for selected filters</span>
                         <span className="text-xs text-slate-400 mt-1">Source: {dataSource}</span>
                       </div>
                    </td>
                  </tr>
                ) : (
                  trades.map((t, i) => (
                    <tr key={t.trade_id || i} className="border-b border-slate-100 hover:bg-slate-50 transition-colors">
                      <td className="px-6 py-4 font-mono text-xs">{t.account_suffix}</td>
                      <td className="px-6 py-4 font-bold text-slate-800">{t.instrument}</td>
                      <td className="px-6 py-4">
                        <span className={`px-2 py-1 rounded text-xs font-bold ${t.direction === 'LONG' ? 'bg-blue-50 text-blue-700' : 'bg-orange-50 text-orange-700'}`}>
                          {t.direction}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-right">
                        <div className="flex flex-col">
                          <span className="font-mono text-slate-900">{fmtCurrency(t.entry_price)}</span>
                          <span className="text-[10px] text-slate-400">{fmtDate(t.entry_time)}</span>
                        </div>
                      </td>
                      <td className="px-6 py-4 text-right">
                        <div className="flex flex-col">
                          <span className="font-mono text-slate-900">{fmtCurrency(t.exit_price)}</span>
                          <span className="text-[10px] text-slate-400">{fmtDate(t.exit_time)}</span>
                        </div>
                      </td>
                      <td className={`px-6 py-4 text-right font-bold font-mono ${t.realized_pl >= 0 ? 'text-emerald-600' : 'text-rose-600'}`}>
                        {fmtCurrency(t.realized_pl)}
                      </td>
                      <td className="px-6 py-4 text-center">
                         <Badge type={t.result === 'WIN' ? 'success' : t.result === 'LOSS' ? 'error' : 'neutral'}>
                           {t.result}
                         </Badge>
                      </td>
                      <td className="px-6 py-4 text-center font-mono text-xs text-slate-500">
                        {t.rr_ratio ? t.rr_ratio.toFixed(2) : '-'}
                      </td>
                      <td className="px-6 py-4 text-right font-mono text-xs text-slate-500">
                        {fmtDuration(t.duration_seconds)}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </section>

      </main>
    </div>
  );
}

export default LocalTradeDashboard;