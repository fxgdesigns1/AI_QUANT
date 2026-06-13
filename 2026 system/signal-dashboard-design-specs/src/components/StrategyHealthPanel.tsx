import { cn } from '../utils/cn';
import type { StrategyHealth } from '../types';

interface StrategyHealthPanelProps {
  strategies: StrategyHealth[];
}

export function StrategyHealthPanel({ strategies }: StrategyHealthPanelProps) {
  const statusConfig = {
    HEALTHY: { bg: 'bg-alpha-green/20', border: 'border-alpha-green/30', text: 'text-alpha-green', icon: '✓' },
    DEGRADED: { bg: 'bg-alpha-amber/20', border: 'border-alpha-amber/30', text: 'text-alpha-amber', icon: '⚠' },
    BLOCKED: { bg: 'bg-alpha-red/20', border: 'border-alpha-red/30', text: 'text-alpha-red', icon: '✕' },
  };

  const totalSignals = strategies.reduce((acc, s) => acc + s.signalsGenerated, 0);
  const totalBlocked = strategies.reduce((acc, s) => acc + s.signalsBlocked, 0);
  const totalTrades = strategies.reduce((acc, s) => acc + s.tradesExecuted, 0);
  const avgWinRate = strategies.reduce((acc, s) => acc + s.winRate, 0) / strategies.length;

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-slate-800">
        <h2 className="text-lg font-semibold text-white">Strategy Health</h2>
        <p className="text-xs text-slate-500">Performance and status of active strategies</p>
      </div>

      <div className="flex-1 overflow-auto p-4 space-y-6">
        {/* Overview Stats */}
        <div className="grid grid-cols-4 gap-3">
          <div className="bg-slate-800/50 rounded-lg p-4 border border-slate-700/50">
            <div className="text-xs text-slate-500 mb-1">Total Signals</div>
            <div className="text-2xl font-bold text-white">{totalSignals}</div>
          </div>
          <div className="bg-slate-800/50 rounded-lg p-4 border border-slate-700/50">
            <div className="text-xs text-slate-500 mb-1">Blocked</div>
            <div className="text-2xl font-bold text-alpha-amber">{totalBlocked}</div>
          </div>
          <div className="bg-slate-800/50 rounded-lg p-4 border border-slate-700/50">
            <div className="text-xs text-slate-500 mb-1">Trades Executed</div>
            <div className="text-2xl font-bold text-alpha-blue">{totalTrades}</div>
          </div>
          <div className="bg-slate-800/50 rounded-lg p-4 border border-slate-700/50">
            <div className="text-xs text-slate-500 mb-1">Avg Win Rate</div>
            <div className={cn('text-2xl font-bold', avgWinRate >= 50 ? 'text-alpha-green' : 'text-alpha-red')}>
              {avgWinRate.toFixed(1)}%
            </div>
          </div>
        </div>

        {/* Strategy Cards */}
        <div className="space-y-4">
          {strategies.map((strategy) => {
            const config = statusConfig[strategy.status];
            return (
              <div key={strategy.id} className={cn('rounded-xl border p-4', config.bg, config.border)}>
                {/* Header */}
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <div className={cn('w-10 h-10 rounded-lg flex items-center justify-center text-lg', config.bg, config.text)}>
                      {config.icon}
                    </div>
                    <div>
                      <h3 className="text-lg font-semibold text-white">{strategy.name.replace(/_/g, ' ')}</h3>
                      <span className={cn('text-xs font-medium', config.text)}>{strategy.status}</span>
                    </div>
                  </div>
                  <div className={cn('px-3 py-1.5 rounded-lg text-sm font-semibold', config.bg, config.text)}>
                    {strategy.winRate}% Win Rate
                  </div>
                </div>

                {/* Metrics Grid */}
                <div className="grid grid-cols-3 gap-3 mb-4">
                  <div className="bg-slate-900/50 rounded-lg p-3">
                    <div className="text-xs text-slate-500 mb-1">Signals Generated</div>
                    <div className="text-xl font-bold text-white">{strategy.signalsGenerated}</div>
                  </div>
                  <div className="bg-slate-900/50 rounded-lg p-3">
                    <div className="text-xs text-slate-500 mb-1">Signals Blocked</div>
                    <div className="text-xl font-bold text-alpha-amber">{strategy.signalsBlocked}</div>
                  </div>
                  <div className="bg-slate-900/50 rounded-lg p-3">
                    <div className="text-xs text-slate-500 mb-1">Paper Trades</div>
                    <div className="text-xl font-bold text-alpha-blue">{strategy.tradesExecuted}</div>
                  </div>
                </div>

                {/* Performance Bars */}
                <div className="space-y-3">
                  <div>
                    <div className="flex items-center justify-between text-xs mb-1">
                      <span className="text-slate-400">Average Confidence</span>
                      <span className="text-white font-medium">{strategy.avgConfidence}%</span>
                    </div>
                    <div className="h-2 bg-slate-700 rounded-full overflow-hidden">
                      <div
                        className={cn('h-full rounded-full', strategy.avgConfidence >= 70 ? 'bg-alpha-green' : strategy.avgConfidence >= 50 ? 'bg-alpha-amber' : 'bg-alpha-red')}
                        style={{ width: `${strategy.avgConfidence}%` }}
                      />
                    </div>
                  </div>
                  <div>
                    <div className="flex items-center justify-between text-xs mb-1">
                      <span className="text-slate-400">Regime Alignment</span>
                      <span className="text-white font-medium">{strategy.regimeAlignment}%</span>
                    </div>
                    <div className="h-2 bg-slate-700 rounded-full overflow-hidden">
                      <div
                        className={cn('h-full rounded-full', strategy.regimeAlignment >= 80 ? 'bg-alpha-green' : strategy.regimeAlignment >= 60 ? 'bg-alpha-amber' : 'bg-alpha-red')}
                        style={{ width: `${strategy.regimeAlignment}%` }}
                      />
                    </div>
                  </div>
                </div>

                {/* Execution Rate */}
                <div className="mt-4 pt-4 border-t border-slate-700/50">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-slate-500">Execution Rate</span>
                    <span className="text-slate-300">
                      {((strategy.tradesExecuted / strategy.signalsGenerated) * 100).toFixed(1)}% of signals
                    </span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
