import { useState, useMemo } from 'react';
import { cn } from '../utils/cn';
import type { Trade, TradeStats } from '../types';

interface TradeJournalPanelProps {
  trades: Trade[];
}

type ViewMode = 'all' | 'by-account' | 'by-strategy' | 'by-instrument' | 'by-session';

export function TradeJournalPanel({ trades }: TradeJournalPanelProps) {
  const [viewMode, setViewMode] = useState<ViewMode>('all');
  const [dateRange, setDateRange] = useState<'7d' | '30d' | '90d' | 'all'>('30d');
  const [selectedTrade, setSelectedTrade] = useState<Trade | null>(null);

  const filteredTrades = useMemo(() => {
    const now = Date.now();
    const ranges = {
      '7d': 7 * 24 * 60 * 60 * 1000,
      '30d': 30 * 24 * 60 * 60 * 1000,
      '90d': 90 * 24 * 60 * 60 * 1000,
      'all': Infinity,
    };
    return trades.filter((t) => now - new Date(t.entryTime).getTime() <= ranges[dateRange]);
  }, [trades, dateRange]);

  const stats = useMemo((): TradeStats => {
    const wins = filteredTrades.filter((t) => t.pnl > 0);
    const losses = filteredTrades.filter((t) => t.pnl < 0);
    
    return {
      totalTrades: filteredTrades.length,
      winRate: filteredTrades.length > 0 ? (wins.length / filteredTrades.length) * 100 : 0,
      lossRate: filteredTrades.length > 0 ? (losses.length / filteredTrades.length) * 100 : 0,
      avgRR: filteredTrades.length > 0 ? filteredTrades.reduce((acc, t) => acc + t.riskReward, 0) / filteredTrades.length : 0,
      avgWin: wins.length > 0 ? wins.reduce((acc, t) => acc + t.pnlPips, 0) / wins.length : 0,
      avgLoss: losses.length > 0 ? Math.abs(losses.reduce((acc, t) => acc + t.pnlPips, 0) / losses.length) : 0,
      expectancy: filteredTrades.length > 0 ? filteredTrades.reduce((acc, t) => acc + t.pnlPips, 0) / filteredTrades.length : 0,
      totalCost: filteredTrades.reduce((acc, t) => acc + t.spread + t.commission, 0),
      avgDuration: filteredTrades.length > 0 ? filteredTrades.reduce((acc, t) => acc + t.duration, 0) / filteredTrades.length : 0,
      avgMAE: filteredTrades.length > 0 ? filteredTrades.reduce((acc, t) => acc + t.mae, 0) / filteredTrades.length : 0,
      avgMFE: filteredTrades.length > 0 ? filteredTrades.reduce((acc, t) => acc + t.mfe, 0) / filteredTrades.length : 0,
    };
  }, [filteredTrades]);

  const formatDuration = (ms: number) => {
    const hours = Math.floor(ms / 3600000);
    const mins = Math.floor((ms % 3600000) / 60000);
    return `${hours}h ${mins}m`;
  };

  const formatDate = (iso: string) => {
    return new Date(iso).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' });
  };

  const groupedData = useMemo(() => {
    const groups: Record<string, Trade[]> = {};
    filteredTrades.forEach((t) => {
      let key: string;
      switch (viewMode) {
        case 'by-account': key = t.account; break;
        case 'by-strategy': key = t.strategy; break;
        case 'by-instrument': key = t.instrument; break;
        case 'by-session': key = t.session; break;
        default: key = 'All Trades';
      }
      if (!groups[key]) groups[key] = [];
      groups[key].push(t);
    });
    return groups;
  }, [filteredTrades, viewMode]);

  const renderEmptyState = () => (
    <div className="flex items-center justify-center h-full">
      <div className="text-center py-12">
        <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-slate-800/50 flex items-center justify-center">
          <svg className="w-8 h-8 text-slate-600" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
            <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/>
            <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>
          </svg>
        </div>
        <p className="text-slate-400 text-sm font-medium mb-1">No trades in selected period</p>
        <p className="text-slate-500 text-xs">Try selecting a longer date range</p>
      </div>
    </div>
  );

  const renderTradesTable = () => (
    <>
      {Object.entries(groupedData).map(([group, groupTrades]) => (
        <div key={group} className="border-b border-slate-800">
          {viewMode !== 'all' && (
            <div className="px-4 py-2 bg-slate-800/30 text-xs font-medium text-slate-400">
              {group.replace(/_/g, ' ')} ({groupTrades.length} trades)
            </div>
          )}
          <table className="w-full text-xs">
            <thead className="bg-slate-900/50 sticky top-0">
              <tr className="text-left text-slate-500">
                <th className="px-4 py-2 font-medium">Time</th>
                <th className="px-4 py-2 font-medium">Instrument</th>
                <th className="px-4 py-2 font-medium">Strategy</th>
                <th className="px-4 py-2 font-medium">Dir</th>
                <th className="px-4 py-2 font-medium text-right">Entry</th>
                <th className="px-4 py-2 font-medium text-right">Exit</th>
                <th className="px-4 py-2 font-medium text-right">PnL</th>
                <th className="px-4 py-2 font-medium text-right">R:R</th>
                <th className="px-4 py-2 font-medium text-right">Conf</th>
              </tr>
            </thead>
            <tbody>
              {groupTrades.map((trade) => (
                <tr
                  key={trade.id}
                  onClick={() => setSelectedTrade(trade)}
                  className="border-t border-slate-800/50 hover:bg-slate-800/30 cursor-pointer transition-colors"
                >
                  <td className="px-4 py-2 text-slate-400 font-mono">{formatDate(trade.entryTime)}</td>
                  <td className="px-4 py-2 text-slate-200 font-medium">{trade.instrument}</td>
                  <td className="px-4 py-2 text-slate-400">{trade.strategy.replace(/_/g, ' ')}</td>
                  <td className="px-4 py-2">
                    <span className={cn('px-1.5 py-0.5 rounded text-[10px] font-medium', trade.direction === 'LONG' ? 'bg-alpha-green/20 text-alpha-green' : 'bg-alpha-red/20 text-alpha-red')}>
                      {trade.direction}
                    </span>
                  </td>
                  <td className="px-4 py-2 text-right font-mono text-slate-400">{trade.entryPrice}</td>
                  <td className="px-4 py-2 text-right font-mono text-slate-400">{trade.exitPrice}</td>
                  <td className={cn('px-4 py-2 text-right font-mono font-medium', trade.pnl >= 0 ? 'text-alpha-green' : 'text-alpha-red')}>
                    {trade.pnl >= 0 ? '+' : ''}{trade.pnlPips}
                  </td>
                  <td className={cn('px-4 py-2 text-right font-mono', trade.riskReward >= 0 ? 'text-alpha-green' : 'text-alpha-red')}>
                    {trade.riskReward.toFixed(2)}
                  </td>
                  <td className="px-4 py-2 text-right text-slate-400">{trade.confidence}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ))}
    </>
  );

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-slate-800">
        <div className="flex items-center justify-between mb-3">
          <div>
            <h2 className="text-lg font-semibold text-white">Trade Journal</h2>
            <p className="text-xs text-slate-500">{filteredTrades.length} trades in selected period</p>
          </div>
          <div className="flex items-center gap-2">
            {(['7d', '30d', '90d', 'all'] as const).map((range) => (
              <button
                key={range}
                onClick={() => setDateRange(range)}
                className={cn(
                  'px-2.5 py-1 rounded text-xs font-medium transition-colors',
                  dateRange === range ? 'bg-alpha-blue text-white' : 'bg-slate-800 text-slate-400 hover:text-white'
                )}
              >
                {range === 'all' ? 'All' : range}
              </button>
            ))}
          </div>
        </div>
        <div className="flex items-center gap-2">
          {(['all', 'by-strategy', 'by-instrument', 'by-session'] as const).map((mode) => (
            <button
              key={mode}
              onClick={() => setViewMode(mode)}
              className={cn(
                'px-2.5 py-1 rounded text-xs transition-colors',
                viewMode === mode ? 'bg-slate-700 text-white' : 'text-slate-500 hover:text-slate-300'
              )}
            >
              {mode.replace('by-', '').replace('-', ' ').charAt(0).toUpperCase() + mode.replace('by-', '').slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Stats Cards */}
      <div className="px-4 py-3 border-b border-slate-800 bg-slate-900/50">
        <div className="grid grid-cols-6 gap-3">
          <div className="bg-slate-800/50 p-3 rounded-lg">
            <span className="text-xs text-slate-500">Win Rate</span>
            <div className={cn('text-xl font-bold', stats.winRate >= 50 ? 'text-alpha-green' : 'text-alpha-red')}>
              {stats.winRate.toFixed(1)}%
            </div>
          </div>
          <div className="bg-slate-800/50 p-3 rounded-lg">
            <span className="text-xs text-slate-500">Avg R:R</span>
            <div className={cn('text-xl font-bold', stats.avgRR >= 1 ? 'text-alpha-green' : 'text-alpha-amber')}>
              {stats.avgRR.toFixed(2)}
            </div>
          </div>
          <div className="bg-slate-800/50 p-3 rounded-lg">
            <span className="text-xs text-slate-500">Expectancy</span>
            <div className={cn('text-xl font-bold', stats.expectancy >= 0 ? 'text-alpha-green' : 'text-alpha-red')}>
              {stats.expectancy >= 0 ? '+' : ''}{stats.expectancy.toFixed(1)}
            </div>
          </div>
          <div className="bg-slate-800/50 p-3 rounded-lg">
            <span className="text-xs text-slate-500">Avg Win</span>
            <div className="text-xl font-bold text-alpha-green">+{stats.avgWin.toFixed(1)}</div>
          </div>
          <div className="bg-slate-800/50 p-3 rounded-lg">
            <span className="text-xs text-slate-500">Avg Loss</span>
            <div className="text-xl font-bold text-alpha-red">-{stats.avgLoss.toFixed(1)}</div>
          </div>
          <div className="bg-slate-800/50 p-3 rounded-lg">
            <span className="text-xs text-slate-500">Total Cost</span>
            <div className="text-xl font-bold text-slate-300">{stats.totalCost.toFixed(1)}</div>
          </div>
        </div>
        <div className="grid grid-cols-4 gap-3 mt-3">
          <div className="bg-slate-800/30 p-2 rounded">
            <span className="text-[10px] text-slate-500">Avg Duration</span>
            <div className="text-sm font-medium text-slate-300">{formatDuration(stats.avgDuration)}</div>
          </div>
          <div className="bg-slate-800/30 p-2 rounded">
            <span className="text-[10px] text-slate-500">Avg MAE</span>
            <div className="text-sm font-medium text-alpha-red">{stats.avgMAE.toFixed(1)} pips</div>
          </div>
          <div className="bg-slate-800/30 p-2 rounded">
            <span className="text-[10px] text-slate-500">Avg MFE</span>
            <div className="text-sm font-medium text-alpha-green">+{stats.avgMFE.toFixed(1)} pips</div>
          </div>
          <div className="bg-slate-800/30 p-2 rounded">
            <span className="text-[10px] text-slate-500">Total Trades</span>
            <div className="text-sm font-medium text-slate-300">{stats.totalTrades}</div>
          </div>
        </div>
      </div>

      {/* Trades Table */}
      <div className="flex-1 overflow-auto">
        {filteredTrades.length === 0 ? renderEmptyState() : renderTradesTable()}
      </div>

      {/* Trade Detail Modal */}
      {selectedTrade && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4" onClick={() => setSelectedTrade(null)}>
          <div className="bg-slate-900 rounded-xl border border-slate-700 max-w-md w-full" onClick={(e) => e.stopPropagation()}>
            <div className="p-4 border-b border-slate-800 flex items-center justify-between">
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-lg font-bold text-white">{selectedTrade.instrument}</span>
                  <span className={cn('px-2 py-0.5 rounded text-xs font-medium', selectedTrade.direction === 'LONG' ? 'bg-alpha-green/20 text-alpha-green' : 'bg-alpha-red/20 text-alpha-red')}>
                    {selectedTrade.direction}
                  </span>
                </div>
                <span className="text-xs text-slate-500 font-mono">{selectedTrade.id}</span>
              </div>
              <button onClick={() => setSelectedTrade(null)} className="p-1 hover:bg-slate-800 rounded">
                <svg className="w-5 h-5 text-slate-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                  <path d="M18 6 6 18M6 6l12 12"/>
                </svg>
              </button>
            </div>
            <div className="p-4 space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div className="bg-slate-800/50 p-3 rounded-lg">
                  <span className="text-xs text-slate-500">P&L (pips)</span>
                  <div className={cn('text-2xl font-bold', selectedTrade.pnl >= 0 ? 'text-alpha-green' : 'text-alpha-red')}>
                    {selectedTrade.pnl >= 0 ? '+' : ''}{selectedTrade.pnlPips}
                  </div>
                </div>
                <div className="bg-slate-800/50 p-3 rounded-lg">
                  <span className="text-xs text-slate-500">Risk:Reward</span>
                  <div className={cn('text-2xl font-bold', selectedTrade.riskReward >= 0 ? 'text-alpha-green' : 'text-alpha-red')}>
                    {selectedTrade.riskReward.toFixed(2)}
                  </div>
                </div>
              </div>
              <div className="grid grid-cols-3 gap-2 text-xs">
                <div className="bg-slate-800/30 p-2 rounded">
                  <span className="text-slate-500">MAE</span>
                  <div className="font-medium text-alpha-red">{selectedTrade.mae}</div>
                </div>
                <div className="bg-slate-800/30 p-2 rounded">
                  <span className="text-slate-500">MFE</span>
                  <div className="font-medium text-alpha-green">+{selectedTrade.mfe}</div>
                </div>
                <div className="bg-slate-800/30 p-2 rounded">
                  <span className="text-slate-500">Duration</span>
                  <div className="font-medium text-slate-300">{formatDuration(selectedTrade.duration)}</div>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="bg-slate-800/30 p-2 rounded">
                  <span className="text-slate-500">Spread</span>
                  <div className="font-medium text-slate-300">{selectedTrade.spread}</div>
                </div>
                <div className="bg-slate-800/30 p-2 rounded">
                  <span className="text-slate-500">Commission</span>
                  <div className="font-medium text-slate-300">{selectedTrade.commission}</div>
                </div>
              </div>
              <div className="text-xs text-slate-500 pt-2 border-t border-slate-800">
                <div className="flex justify-between">
                  <span>Session: {selectedTrade.session}</span>
                  <span>Regime: {selectedTrade.regime}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
