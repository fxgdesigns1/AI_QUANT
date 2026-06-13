import { cn } from '../utils/cn';
import type { Signal } from '../types';

interface SignalCardProps {
  signal: Signal;
  onClick?: () => void;
}

export function SignalCard({ signal, onClick }: SignalCardProps) {
  const statusConfig = {
    FORMING: { bg: 'bg-alpha-amber/10', border: 'border-alpha-amber/30', text: 'text-alpha-amber' },
    CONFIRMED: { bg: 'bg-alpha-green/10', border: 'border-alpha-green/30', text: 'text-alpha-green' },
    INVALIDATED: { bg: 'bg-alpha-red/10', border: 'border-alpha-red/30', text: 'text-alpha-red' },
    EXPIRED: { bg: 'bg-slate-700/50', border: 'border-slate-600', text: 'text-slate-400' },
  };

  const gateConfig = {
    OPEN: { bg: 'bg-alpha-green/20', text: 'text-alpha-green' },
    RESTRICTED: { bg: 'bg-alpha-amber/20', text: 'text-alpha-amber' },
    CLOSED: { bg: 'bg-alpha-red/20', text: 'text-alpha-red' },
  };

  const newsConfig = {
    NONE: null,
    LOW: { bg: 'bg-slate-600', text: 'text-slate-300' },
    MEDIUM: { bg: 'bg-alpha-amber/30', text: 'text-alpha-amber' },
    HIGH: { bg: 'bg-alpha-red/30', text: 'text-alpha-red' },
  };

  const trendIcon = {
    RISING: '↑',
    FALLING: '↓',
    STABLE: '→',
  };

  const trendColor = {
    RISING: 'text-alpha-green',
    FALLING: 'text-alpha-red',
    STABLE: 'text-slate-400',
  };

  const formatTimeRemaining = (isoEnd: string) => {
    const diff = new Date(isoEnd).getTime() - Date.now();
    if (diff <= 0) return 'Expired';
    const mins = Math.floor(diff / 60000);
    const hours = Math.floor(mins / 60);
    if (hours > 0) return `${hours}h ${mins % 60}m`;
    return `${mins}m`;
  };

  const config = statusConfig[signal.status];
  const isActive = signal.status !== 'INVALIDATED' && signal.status !== 'EXPIRED';

  return (
    <div
      onClick={onClick}
      className={cn(
        'p-4 rounded-lg border transition-all cursor-pointer',
        config.bg,
        config.border,
        'hover:bg-opacity-80'
      )}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-lg font-semibold text-white">{signal.instrument}</span>
            <span className={cn(
              'px-2 py-0.5 rounded text-xs font-medium',
              signal.direction === 'LONG' ? 'bg-alpha-green/20 text-alpha-green' : 'bg-alpha-red/20 text-alpha-red'
            )}>
              {signal.direction}
            </span>
          </div>
          <span className="text-xs text-slate-400 font-mono">{signal.id}</span>
        </div>
        <div className={cn('px-2 py-1 rounded text-xs font-medium', config.bg, config.text)}>
          {signal.status}
        </div>
      </div>

      {/* Confidence Bar */}
      <div className="mb-3">
        <div className="flex items-center justify-between mb-1">
          <span className="text-xs text-slate-400">Confidence</span>
          <div className="flex items-center gap-1">
            <span className={cn('text-xs font-medium', trendColor[signal.confidenceTrend])}>
              {trendIcon[signal.confidenceTrend]}
            </span>
            <span className="text-sm font-semibold text-white">{signal.confidence}%</span>
          </div>
        </div>
        <div className="h-2 bg-slate-700 rounded-full overflow-hidden">
          <div
            className={cn(
              'h-full rounded-full transition-all duration-500',
              signal.confidence >= 70 ? 'bg-alpha-green' : signal.confidence >= 50 ? 'bg-alpha-amber' : 'bg-alpha-red'
            )}
            style={{ width: `${signal.confidence}%` }}
          />
        </div>
      </div>

      {/* Details Grid */}
      <div className="grid grid-cols-2 gap-2 text-xs">
        <div className="flex items-center justify-between bg-slate-800/50 px-2 py-1.5 rounded">
          <span className="text-slate-500">Strategy</span>
          <span className="text-slate-300 font-mono text-[10px]">{signal.strategy.replace('_', ' ')}</span>
        </div>
        <div className="flex items-center justify-between bg-slate-800/50 px-2 py-1.5 rounded">
          <span className="text-slate-500">Regime</span>
          <span className="text-slate-300">{signal.regime}</span>
        </div>
        <div className="flex items-center justify-between bg-slate-800/50 px-2 py-1.5 rounded">
          <span className="text-slate-500">Gate</span>
          <span className={cn('px-1.5 py-0.5 rounded text-[10px] font-medium', gateConfig[signal.sessionGate].bg, gateConfig[signal.sessionGate].text)}>
            {signal.sessionGate}
          </span>
        </div>
        <div className="flex items-center justify-between bg-slate-800/50 px-2 py-1.5 rounded">
          <span className="text-slate-500">Validity</span>
          <span className={cn('font-mono', isActive ? 'text-slate-300' : 'text-slate-500')}>
            {formatTimeRemaining(signal.validityWindowEnd)}
          </span>
        </div>
      </div>

      {/* News Impact Badge */}
      {signal.newsImpact !== 'NONE' && newsConfig[signal.newsImpact] && (
        <div className={cn('mt-2 px-2 py-1 rounded text-[10px] font-medium flex items-center gap-1', newsConfig[signal.newsImpact]!.bg, newsConfig[signal.newsImpact]!.text)}>
          <svg className="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
            <polyline points="14 2 14 8 20 8"/>
          </svg>
          NEWS: {signal.newsImpact} IMPACT
        </div>
      )}

      {/* Reasoning Preview */}
      <div className="mt-3 pt-3 border-t border-slate-700/50">
        <p className="text-xs text-slate-400 line-clamp-2">{signal.reasoning}</p>
      </div>
    </div>
  );
}
