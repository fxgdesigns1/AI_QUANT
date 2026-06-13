/**
 * VM Trade Journal - Authoritative OANDA /trades Version
 * Mirroring Local Dashboard but pointing to VM API
 * 
 * TRUTH SOURCE:
 * - OANDA /v3/accounts/{id}/trades (via /api/vm/trades)
 * - STATS COMPUTED DYNAMICALLY BY TIME WINDOW
 * 
 * LAYOUT:
 * - Header: Title + Source Badge + DATE PICKER
 * - Summary Bar: Global KPIs (Filtered by time)
 * - Controls: Account | Instrument | Strategy
 * - Table: Detailed Trade Journal
 */

import { useState, useEffect } from 'react';

// Adjust API_BASE based on environment or proxy
const API_BASE = '/api/vm';

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

function TradeJournal() {
  // Default date range: Last 30 days
  const today = new Date().toISOString().split('T')[0];
  const lastMonth = new Date();
  lastMonth.setDate(lastMonth.getDate() - 30);
  const lastMonthStr = lastMonth.toISOString().split('T')[0];

  const [dateRange, setDateRange] = useState({ start: lastMonthStr, end: today });
  const [trades, setTrades] = useState([]);
  const [stats, setStats] = useState(null);
  const [meta, setMeta] = useState({ source: 'unknown', confidence: 'UNKNOWN' });
  const [filters, setFilters] = useState({ account_id: '', instrument: '', strategy: '' });
  
  // Available options for dropdowns (derived from loaded trades + known set)
  // Since we only get filtered trades, we might want a separate call for "all possible filters" 
  // or just accumulate them. For simplicity, we'll extract from current view + defaults.
  const [availableAccounts, setAvailableAccounts] = useState([]);
  const [availableInstruments, setAvailableInstruments] = useState([]);
  const [availableStrategies, setAvailableStrategies] = useState([]);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Load data when filters or date range change
  useEffect(() => {
    loadData();
  }, [dateRange, filters]);

    const loadData = async () => {
    if (!dateRange.start || !dateRange.end) return;

    setLoading(true);
    setError(null);
    try {
      // Build query
      const params = new URLSearchParams();
      params.append('start_date', dateRange.start);
      params.append('end_date', dateRange.end);
      if (filters.account_id) params.append('account_id', filters.account_id);
      if (filters.instrument) params.append('instrument', filters.instrument);
      if (filters.strategy) params.append('strategy', filters.strategy);

      // Fetch Trades and Stats from unified journal endpoint
      const res = await fetch(`${API_BASE}/journal/trades?${params.toString()}`);

      if (!res.ok) {
         const errText = await res.text();
         throw new Error(`API Error: ${errText}`);
      }

      const data = await res.json();

      if (data.success) {
        setTrades(data.trades || []);
        setStats(data.stats);
        
        // Update available filters based on data if needed
        const accs = new Set(data.trades.map(t => t.account_id).filter(Boolean));
        const insts = new Set(data.trades.map(t => t.instrument).filter(Boolean));
        const strats = new Set(data.trades.map(t => t.strategy).filter(Boolean));
        
        if (availableAccounts.length === 0 && accs.size > 0) setAvailableAccounts([...accs].sort());
        if (availableInstruments.length === 0 && insts.size > 0) setAvailableInstruments([...insts].sort());
        if (availableStrategies.length === 0 && strats.size > 0) setAvailableStrategies([...strats].sort());

        setMeta({
          source: data.meta.source,
          confidence: data.meta.confidence
        });
      }

    } catch (err) {
      console.error(err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Formatters
  const fmtCurrency = (val) => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(val);
  const fmtDate = (str) => {
    if (!str) return '-';
    // Handle both ISO with Z and without
    return new Date(str.replace('Z', '')).toLocaleString(undefined, { 
      month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', hour12: false 
    });
  };
  const fmtDuration = (secs) => {
    if (!secs) return '-';
    if (secs < 60) return `${secs}s`;
    if (secs < 3600) return `${Math.floor(secs/60)}m`;
    return `${(secs/3600).toFixed(1)}h`;
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-800 font-sans">
      
      {/* Header */}
      <header className="bg-white border-b border-slate-200 px-6 py-4 flex items-center justify-between sticky top-0 z-10 shadow-sm flex-wrap gap-4">
        <div className="flex items-center gap-4">
          <h1 className="text-lg font-bold text-slate-900 tracking-tight">VM Trade Journal</h1>
          <Badge type="success">SOURCE: OANDA (Authoritative)</Badge>
        </div>
        
        {/* Date Range Picker */}
        <div className="flex items-center gap-2 bg-slate-100 p-1.5 rounded-lg border border-slate-200">
          <span className="text-xs font-bold text-slate-500 px-2">RANGE:</span>
          <input 
            type="date" 
            className="bg-white border border-slate-300 rounded px-2 py-1 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
            value={dateRange.start}
            onChange={(e) => setDateRange(prev => ({ ...prev, start: e.target.value }))}
          />
          <span className="text-slate-400">→</span>
          <input 
            type="date" 
            className="bg-white border border-slate-300 rounded px-2 py-1 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
            value={dateRange.end}
            onChange={(e) => setDateRange(prev => ({ ...prev, end: e.target.value }))}
          />
        </div>

        <div className="text-xs text-slate-400 font-mono hidden md:block">
          Sync: {new Date().toLocaleTimeString()}
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8">

        {/* Error */}
        {error && (
          <div className="bg-red-50 border-l-4 border-red-500 p-4 mb-6 text-red-700">
            <strong>System Error:</strong> {error}
          </div>
        )}

        {/* Top Summary Bar (Stats from API) */}
        {stats && (
          <section className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-8">
            <SummaryMetric label="Trades" value={stats.trades} />
            <SummaryMetric 
              label="Net P&L" 
              value={fmtCurrency(stats.total_pl)} 
              color={stats.total_pl >= 0 ? 'text-emerald-600' : 'text-rose-600'} 
            />
            <SummaryMetric 
              label="Win Rate" 
              value={stats.trades > 0 && stats.win_rate !== null ? `${stats.win_rate.toFixed(1)}%` : '-'}
              subtext={`${stats.wins}W - ${stats.losses}L`}
              color={stats.win_rate >= 50 ? 'text-emerald-600' : 'text-amber-600'}
            />
            <SummaryMetric 
              label="Expectancy" 
              value={stats.trades > 0 && stats.expectancy !== null ? fmtCurrency(stats.expectancy) : '-'} 
              color={stats.expectancy >= 0 ? 'text-emerald-600' : 'text-rose-600'}
            />
            <SummaryMetric 
              label="Status" 
              value={meta.confidence} 
              color={meta.confidence === 'HIGH' ? 'text-emerald-600' : 'text-rose-600'}
              subtext="Data Confidence"
            />
          </section>
        )}

        {/* Controls */}
        <section className="bg-white rounded-lg border border-slate-200 p-4 mb-6 shadow-sm flex flex-col md:flex-row gap-6 items-end">
          <div className="flex-1 w-full">
            <label htmlFor="account-select" className="block text-xs font-bold text-slate-500 uppercase mb-1">Account</label>
            <select 
              id="account-select"
              className="w-full bg-slate-50 border border-slate-300 text-slate-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 p-2.5"
              value={filters.account_id}
              onChange={(e) => setFilters(prev => ({ ...prev, account_id: e.target.value }))}
            >
              <option value="">ALL ACCOUNTS</option>
              {availableAccounts.map(acc => (
                <option key={acc} value={acc}>{acc}</option>
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
              {availableInstruments.map(inst => (
                <option key={inst} value={inst}>{inst}</option>
              ))}
            </select>
          </div>
          <div className="flex-1 w-full">
            <label htmlFor="strategy-select" className="block text-xs font-bold text-slate-500 uppercase mb-1">Strategy</label>
            <select 
              id="strategy-select"
              className="w-full bg-slate-50 border border-slate-300 text-slate-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 p-2.5"
              value={filters.strategy}
              onChange={(e) => setFilters(prev => ({ ...prev, strategy: e.target.value }))}
            >
              <option value="">ALL STRATEGIES</option>
              {availableStrategies.map(strat => (
                <option key={strat} value={strat}>{strat}</option>
              ))}
            </select>
          </div>
          <div className="pb-1">
             <button 
               onClick={() => setFilters({ account_id: '', instrument: '', strategy: '' })}
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
                  <th className="px-6 py-3">Strategy</th>
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
                    <td colSpan="10" className="px-6 py-12 text-center text-slate-400">
                      Loading authoritative data...
                    </td>
                  </tr>
                ) : trades.length === 0 ? (
                  <tr>
                    <td colSpan="10" className="px-6 py-12 text-center">
                       <div className="flex flex-col items-center">
                         <span className="text-2xl mb-2">📭</span>
                         <span className="font-bold text-slate-700">No closed trades in selected range</span>
                         <span className="text-xs text-slate-400 mt-1">Source: {meta.source}</span>
                       </div>
                    </td>
                  </tr>
                ) : (
                  trades.map((t, i) => (
                    <tr key={t.trade_id || i} className="border-b border-slate-100 hover:bg-slate-50 transition-colors">
                      <td className="px-6 py-4 font-mono text-xs">{t.account_suffix || t.account_id}</td>
                      <td className="px-6 py-4 font-mono text-xs text-slate-500">{t.strategy || '-'}</td>
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

export default TradeJournal;
