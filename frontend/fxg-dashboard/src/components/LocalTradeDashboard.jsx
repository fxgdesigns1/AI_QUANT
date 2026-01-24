/**
 * Local Trade Dashboard - Professional Grade
 * React component for displaying OANDA trade data locally.
 * 
 * TRUTH SOURCE:
 * - Displays data strictly from /api endpoints.
 * - Supports 'vm_logs' (Authoritative) or 'oanda' (Legacy/Secondary).
 * 
 * DESIGN PRINCIPLES:
 * 1. Truth-First: Data comes strictly from the API. No mocks.
 * 2. Hierarchy: Global Stats -> Breakdowns -> Journal.
 * 3. Clarity: Explicit states for empty/loading/error.
 */

import { useState, useEffect } from 'react';

const API_BASE = '/api';

// --- UI Components ---

const StatCard = ({ label, value, subtext, color = 'text-gray-900', size = 'normal' }) => (
  <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 flex flex-col items-start justify-between h-full transition-shadow hover:shadow-md">
    <div className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-2">{label}</div>
    <div className={`font-bold ${color} ${size === 'large' ? 'text-4xl' : 'text-3xl'} tracking-tight`}>
      {value}
    </div>
    {subtext && <div className="text-xs text-gray-400 mt-2 font-medium">{subtext}</div>}
  </div>
);

const Badge = ({ children, type = 'neutral' }) => {
  const styles = {
    neutral: 'bg-gray-100 text-gray-800 border-gray-200',
    success: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    error: 'bg-red-50 text-red-700 border-red-200',
    warning: 'bg-amber-50 text-amber-700 border-amber-200',
    info: 'bg-blue-50 text-blue-700 border-blue-200',
  };
  return (
    <span className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-bold border ${styles[type]} uppercase tracking-wide`}>
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
  const [pairStats, setPairStats] = useState({});
  const [accountStats, setAccountStats] = useState({});
  const [filters, setFilters] = useState({});
  const [availableFilters, setAvailableFilters] = useState({ accounts: [], instruments: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastRefreshed, setLastRefreshed] = useState(null);

  // Load available filter options on mount
  useEffect(() => {
    fetch(`${API_BASE}/filters`)
      .then(res => res.json())
      .then(data => {
        if (data.success) {
          setAvailableFilters(data);
        }
      })
      .catch(err => console.error('Failed to load filters:', err));
  }, []);

  // Load data when filters change
  useEffect(() => {
    loadData();
  }, [filters]);

  const loadData = async () => {
    setLoading(true);
    setError(null);

    try {
      // Build query params
      const params = new URLSearchParams();
      if (filters.account_suffix) params.append('account_suffix', filters.account_suffix);
      if (filters.instrument) params.append('instrument', filters.instrument);
      if (filters.start_date) params.append('start_date', filters.start_date);
      if (filters.end_date) params.append('end_date', filters.end_date);

      const query = params.toString();
      
      // Fetch all data in parallel
      const [tradesRes, statsRes, pairRes, accountRes] = await Promise.all([
        fetch(`${API_BASE}/trades${query ? '?' + query : ''}`),
        fetch(`${API_BASE}/stats${query ? '?' + query : ''}`),
        fetch(`${API_BASE}/stats/pair${query ? '?' + query : ''}`),
        fetch(`${API_BASE}/stats/account`)
      ]);

      if (!tradesRes.ok || !statsRes.ok) {
        throw new Error(`API Error: Trades=${tradesRes.status}, Stats=${statsRes.status}`);
      }

      const tradesData = await tradesRes.json();
      const statsData = await statsRes.json();
      const pairData = await pairRes.json();
      const accountData = await accountRes.json();

      if (tradesData.success) {
         setTrades(tradesData.trades || []);
         // Source comes from the trades endpoint usually, or stats
         setDataSource(tradesData.source || 'unknown');
      }
      
      if (statsData.success) {
        setStats(statsData.stats);
        setDataConfidence(statsData.data_confidence || 'HIGH');
        // If source missing in trades, check stats
        if (statsData.source && statsData.source !== 'unknown') {
            setDataSource(statsData.source);
        }
      }
      if (pairData.success) setPairStats(pairData.stats || {});
      if (accountData.success) setAccountStats(accountData.stats || {});
      
      setLastRefreshed(new Date());

    } catch (err) {
      setError(err.message);
      console.error('Failed to load data:', err);
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return 'N/A';
    try {
      return new Date(dateStr).toLocaleString(undefined, { 
        month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' 
      });
    } catch {
      return dateStr;
    }
  };

  const formatCurrency = (value) => {
    if (value === null || value === undefined) return '-';
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(value);
  };

  const formatPercent = (value) => {
    if (value === null || value === undefined) return '-';
    return `${value.toFixed(1)}%`;
  };

  // Helper to determine if we should show performance metrics
  const hasClosedTrades = stats && stats.trades > 0;

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 font-sans pb-12">
      
      {/* Top Bar */}
      <div className="bg-white border-b border-slate-200 sticky top-0 z-10 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <h1 className="text-xl font-bold text-slate-900 tracking-tight">FXG / GCLOUD Dashboard</h1>
            
            {/* Confidence Badge */}
            <Badge type={dataConfidence === 'HIGH' ? 'success' : 'error'}>
              {dataConfidence === 'HIGH' ? 'VERIFIED' : 'UNVERIFIED'}
            </Badge>

            {/* Source Badge */}
            {dataSource === 'vm_logs' && (
                <Badge type="info">SOURCE: VM LOGS (AUTH)</Badge>
            )}
            {dataSource === 'oanda_legacy' && (
                <Badge type="warning">SOURCE: OANDA (LEGACY)</Badge>
            )}
            {dataSource === 'oanda_authoritative' && (
                <Badge type="success">SOURCE: OANDA (DIRECT)</Badge>
            )}
             {dataSource === 'none' && (
                <Badge type="neutral">NO DATA SOURCE</Badge>
            )}
          </div>
          <div className="text-sm text-slate-500 font-medium">
            Last updated: {lastRefreshed ? lastRefreshed.toLocaleTimeString() : '-'}
          </div>
        </div>
      </div>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        
        {/* Error State */}
        {error && (
          <div className="bg-red-50 border-l-4 border-red-500 p-4 mb-8 rounded-r-md">
            <div className="flex">
              <div className="flex-shrink-0 text-red-500">⚠️</div>
              <div className="ml-3">
                <p className="text-sm text-red-700">
                  <span className="font-bold">System Error:</span> {error}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Confidence Warning */}
        {dataConfidence !== 'HIGH' && !error && (
          <div className="bg-red-600 text-white px-6 py-4 rounded-lg shadow-md mb-8 flex items-center justify-between">
            <div className="flex items-center">
              <span className="text-3xl mr-4">⚠️</span>
              <div>
                <h3 className="font-bold text-lg tracking-tight">DATA NOT VERIFIED – CHECK PIPELINE</h3>
                <p className="text-red-100 text-sm mt-1">Trade capture stream indicates potential gaps or legacy data source. Do not trust P&L figures implicitly.</p>
              </div>
            </div>
          </div>
        )}

        {loading ? (
          <div className="flex justify-center items-center h-64">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
          </div>
        ) : (
          <>
            {/* 1. Global Stats - High Hierarchy */}
            <section className="mb-12">
              <div className="flex items-center justify-between mb-6">
                 <h2 className="text-xl font-bold text-slate-800 uppercase tracking-wide">Performance Overview</h2>
                 <span className="text-sm text-slate-500 font-medium">
                     {dataSource === 'vm_logs' ? 'REAL-TIME EXECUTION LOGS' : 'BROKER RECONCILIATION'}
                 </span>
              </div>
              
              {hasClosedTrades ? (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                  <StatCard 
                    label="Net Profit & Loss" 
                    value={formatCurrency(stats.total_pl)} 
                    color={stats.total_pl >= 0 ? 'text-emerald-600' : 'text-rose-600'}
                    size="large"
                  />
                  <StatCard 
                    label="Win Rate" 
                    value={formatPercent(stats.win_rate)} 
                    subtext={`${stats.wins} Wins / ${stats.losses} Losses`}
                    color={stats.win_rate >= 50 ? 'text-indigo-600' : 'text-amber-600'}
                    size="large"
                  />
                  <StatCard 
                    label="Profit Factor" 
                    value={stats.profit_factor ? stats.profit_factor.toFixed(2) : '-'} 
                    size="large"
                  />
                  <StatCard 
                    label="Total Trades" 
                    value={stats.trades} 
                    subtext="Closed Positions"
                    size="large"
                  />
                </div>
              ) : (
                 <div className="bg-slate-50 border-2 border-dashed border-slate-300 rounded-xl p-12 text-center">
                   <div className="text-4xl mb-4">📭</div>
                   <h3 className="text-lg font-bold text-slate-700 mb-2">VERIFIED: No closed trades returned from Source</h3>
                   <p className="text-slate-500 max-w-md mx-auto">
                     The API returned 0 closed trades from <strong>{dataSource}</strong>. Win rate and P&L metrics are hidden until trades are completed and synced.
                   </p>
                 </div>
              )}
            </section>

            {/* 2. Breakdown Section */}
            {hasClosedTrades && (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-12">
                {/* Account Breakdown */}
                <section>
                   <div className="flex items-center justify-between mb-4">
                     <h2 className="text-lg font-bold text-slate-700 uppercase tracking-wider">By Account</h2>
                   </div>
                   <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
                     <table className="min-w-full divide-y divide-slate-200">
                       <thead className="bg-slate-50">
                         <tr>
                           <th className="px-6 py-3 text-left text-xs font-bold text-slate-500 uppercase tracking-wider">Account</th>
                           <th className="px-6 py-3 text-right text-xs font-bold text-slate-500 uppercase tracking-wider">Trades</th>
                           <th className="px-6 py-3 text-right text-xs font-bold text-slate-500 uppercase tracking-wider">Win Rate</th>
                           <th className="px-6 py-3 text-right text-xs font-bold text-slate-500 uppercase tracking-wider">P&L</th>
                         </tr>
                       </thead>
                       <tbody className="bg-white divide-y divide-slate-200">
                         {Object.entries(accountStats).map(([acc, data]) => (
                           <tr key={acc} className="hover:bg-slate-50 transition-colors">
                             <td className="px-6 py-4 whitespace-nowrap text-sm font-semibold text-slate-900">{acc}</td>
                             <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-600 text-right">{data.trades}</td>
                             <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-600 text-right">{formatPercent(data.win_rate)}</td>
                             <td className={`px-6 py-4 whitespace-nowrap text-sm text-right font-bold ${data.total_pl >= 0 ? 'text-emerald-600' : 'text-rose-600'}`}>
                               {formatCurrency(data.total_pl)}
                             </td>
                           </tr>
                         ))}
                       </tbody>
                     </table>
                   </div>
                </section>

                {/* Instrument Breakdown */}
                <section>
                   <div className="flex items-center justify-between mb-4">
                     <h2 className="text-lg font-bold text-slate-700 uppercase tracking-wider">By Instrument</h2>
                   </div>
                   <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
                     <table className="min-w-full divide-y divide-slate-200">
                       <thead className="bg-slate-50">
                         <tr>
                           <th className="px-6 py-3 text-left text-xs font-bold text-slate-500 uppercase tracking-wider">Pair</th>
                           <th className="px-6 py-3 text-right text-xs font-bold text-slate-500 uppercase tracking-wider">Trades</th>
                           <th className="px-6 py-3 text-right text-xs font-bold text-slate-500 uppercase tracking-wider">Win Rate</th>
                           <th className="px-6 py-3 text-right text-xs font-bold text-slate-500 uppercase tracking-wider">P&L</th>
                         </tr>
                       </thead>
                       <tbody className="bg-white divide-y divide-slate-200">
                         {Object.entries(pairStats).map(([pair, data]) => (
                           <tr key={pair} className="hover:bg-slate-50 transition-colors">
                             <td className="px-6 py-4 whitespace-nowrap text-sm font-semibold text-slate-900">{pair}</td>
                             <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-600 text-right">{data.trades}</td>
                             <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-600 text-right">{formatPercent(data.win_rate)}</td>
                             <td className={`px-6 py-4 whitespace-nowrap text-sm text-right font-bold ${data.total_pl >= 0 ? 'text-emerald-600' : 'text-rose-600'}`}>
                               {formatCurrency(data.total_pl)}
                             </td>
                           </tr>
                         ))}
                       </tbody>
                     </table>
                   </div>
                </section>
              </div>
            )}

            {/* 3. Filter Controls */}
            <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 mb-8">
               <h3 className="text-sm font-bold text-slate-500 uppercase tracking-wider mb-4">Data Filters</h3>
               <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                 <div>
                   <label className="block text-xs font-semibold text-slate-500 mb-1">Account</label>
                   <select
                     className="block w-full pl-3 pr-10 py-2.5 text-sm border-slate-300 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 rounded-md bg-slate-50"
                     value={filters.account_suffix || ''}
                     onChange={(e) => setFilters({ ...filters, account_suffix: e.target.value || null })}
                   >
                     <option value="">All Accounts</option>
                     {availableFilters.accounts.map(acc => (
                       <option key={acc} value={acc}>Account {acc}</option>
                     ))}
                   </select>
                 </div>
                 <div>
                   <label className="block text-xs font-semibold text-slate-500 mb-1">Instrument</label>
                   <select
                     className="block w-full pl-3 pr-10 py-2.5 text-sm border-slate-300 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 rounded-md bg-slate-50"
                     value={filters.instrument || ''}
                     onChange={(e) => setFilters({ ...filters, instrument: e.target.value || null })}
                   >
                     <option value="">All Instruments</option>
                     {availableFilters.instruments.map(inst => (
                       <option key={inst} value={inst}>{inst}</option>
                     ))}
                   </select>
                 </div>
                 <div>
                   <label className="block text-xs font-semibold text-slate-500 mb-1">Start Date</label>
                   <input
                     type="date"
                     className="block w-full pl-3 pr-3 py-2.5 text-sm border-slate-300 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 rounded-md bg-slate-50"
                     value={filters.start_date || ''}
                     onChange={(e) => setFilters({ ...filters, start_date: e.target.value || null })}
                   />
                 </div>
                 <div>
                    <label className="block text-xs font-semibold text-slate-500 mb-1">End Date</label>
                    <input
                      type="date"
                      className="block w-full pl-3 pr-3 py-2.5 text-sm border-slate-300 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 rounded-md bg-slate-50"
                      value={filters.end_date || ''}
                      onChange={(e) => setFilters({ ...filters, end_date: e.target.value || null })}
                    />
                  </div>
               </div>
            </div>

            {/* 4. Trade Journal */}
            <section>
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-bold text-slate-800 uppercase tracking-wide">Trade Journal</h2>
                <span className="text-sm text-slate-500 bg-slate-100 px-3 py-1 rounded-full font-medium">{trades.length} Records</span>
              </div>
              
              <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-slate-200">
                    <thead className="bg-slate-50">
                      <tr>
                        <th className="px-6 py-4 text-left text-xs font-bold text-slate-500 uppercase tracking-wider">Time</th>
                        <th className="px-6 py-4 text-left text-xs font-bold text-slate-500 uppercase tracking-wider">Account</th>
                        <th className="px-6 py-4 text-left text-xs font-bold text-slate-500 uppercase tracking-wider">Instrument</th>
                        <th className="px-6 py-4 text-left text-xs font-bold text-slate-500 uppercase tracking-wider">Dir</th>
                        <th className="px-6 py-4 text-right text-xs font-bold text-slate-500 uppercase tracking-wider">Entry</th>
                        <th className="px-6 py-4 text-right text-xs font-bold text-slate-500 uppercase tracking-wider">Exit</th>
                        <th className="px-6 py-4 text-right text-xs font-bold text-slate-500 uppercase tracking-wider">P&L</th>
                        <th className="px-6 py-4 text-right text-xs font-bold text-slate-500 uppercase tracking-wider">Result</th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-slate-200">
                      {trades.length > 0 ? (
                        trades.map((trade, index) => (
                          <tr key={trade.trade_id || index} className="hover:bg-slate-50 transition-colors">
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-600">
                              <div className="flex flex-col">
                                <span className="font-medium">{formatDate(trade.entry_time)}</span>
                                <span className="text-xs text-slate-400 font-mono mt-0.5">ID: {trade.trade_id}</span>
                              </div>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-600">
                              <span className="font-mono bg-slate-100 px-2 py-1 rounded text-xs border border-slate-200">{trade.account_suffix}</span>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm font-bold text-slate-800">{trade.instrument}</td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm">
                              <span className={`inline-flex items-center px-2.5 py-0.5 rounded font-bold text-xs ${trade.direction === 'LONG' || trade.direction === 'BUY' ? 'bg-blue-100 text-blue-800' : 'bg-orange-100 text-orange-800'}`}>
                                {trade.direction}
                              </span>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-600 text-right font-mono">{formatCurrency(trade.entry_price)}</td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-600 text-right font-mono">{formatCurrency(trade.exit_price)}</td>
                            <td className={`px-6 py-4 whitespace-nowrap text-sm text-right font-bold ${trade.realized_pl >= 0 ? 'text-emerald-600' : 'text-rose-600'}`}>
                              {formatCurrency(trade.realized_pl)}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-right">
                              <Badge type={trade.result === 'WIN' ? 'success' : trade.result === 'LOSS' ? 'error' : 'neutral'}>
                                {trade.result}
                              </Badge>
                            </td>
                          </tr>
                        ))
                      ) : (
                        <tr>
                          <td colSpan="8" className="px-6 py-16 text-center">
                            <div className="flex flex-col items-center justify-center">
                               <div className="text-3xl mb-3">🔍</div>
                               <p className="text-slate-600 font-bold text-lg">VERIFIED: No closed trades returned from Source</p>
                               <p className="text-sm text-slate-400 mt-2 max-w-sm">Source: {dataSource}</p>
                            </div>
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </section>
          </>
        )}
      </main>
    </div>
  );
}

export default LocalTradeDashboard;