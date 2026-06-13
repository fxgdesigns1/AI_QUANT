import { cn } from '../utils/cn';
import type { MarketOutlook } from '../types';

interface OutlookPanelProps {
  outlook: MarketOutlook;
}

export function OutlookPanel({ outlook }: OutlookPanelProps) {
  const biasConfig = {
    BULLISH: { color: 'text-alpha-green', bg: 'bg-alpha-green/20', icon: '↑' },
    BEARISH: { color: 'text-alpha-red', bg: 'bg-alpha-red/20', icon: '↓' },
    NEUTRAL: { color: 'text-slate-400', bg: 'bg-slate-600/20', icon: '→' },
    MIXED: { color: 'text-alpha-amber', bg: 'bg-alpha-amber/20', icon: '↔' },
  };

  const overallConfig = biasConfig[outlook.overall];

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-slate-800">
        <h2 className="text-lg font-semibold text-white">Market Outlook</h2>
        <p className="text-xs text-slate-500">System's view on market conditions</p>
      </div>

      <div className="flex-1 overflow-auto p-4 space-y-6">
        {/* Overall Outlook */}
        <div className={cn('p-6 rounded-xl border', overallConfig.bg, 'border-current/30')}>
          <div className="flex items-center justify-between">
            <div>
              <div className="text-xs text-slate-500 uppercase tracking-wider mb-1">Overall Market Bias</div>
              <div className={cn('text-3xl font-bold flex items-center gap-2', overallConfig.color)}>
                <span>{overallConfig.icon}</span>
                {outlook.overall}
              </div>
            </div>
            <div className="text-right">
              <div className="text-xs text-slate-500 mb-1">Confidence</div>
              <div className="text-2xl font-bold text-white">{outlook.confidence}%</div>
              <div className="w-20 h-2 bg-slate-700 rounded-full mt-1 overflow-hidden">
                <div
                  className={cn('h-full rounded-full', overallConfig.bg.replace('/20', ''))}
                  style={{ width: `${outlook.confidence}%` }}
                />
              </div>
            </div>
          </div>
        </div>

        {/* Instrument Biases */}
        <div>
          <h3 className="text-sm font-medium text-slate-400 mb-3">Instrument Outlook</h3>
          <div className="grid grid-cols-2 gap-3">
            {Object.entries(outlook.instruments).map(([instrument, data]) => {
              const config = biasConfig[data.bias];
              return (
                <div key={instrument} className="bg-slate-800/50 rounded-lg p-3 border border-slate-700/50">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-white">{instrument}</span>
                    <span className={cn('text-lg', config.color)}>{config.icon}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className={cn('text-xs font-medium px-2 py-0.5 rounded', config.bg, config.color)}>
                      {data.bias}
                    </span>
                    <span className="text-xs text-slate-400">{data.confidence}%</span>
                  </div>
                  <div className="mt-2 h-1.5 bg-slate-700 rounded-full overflow-hidden">
                    <div
                      className={cn('h-full rounded-full transition-all', 
                        data.bias === 'BULLISH' ? 'bg-alpha-green' : 
                        data.bias === 'BEARISH' ? 'bg-alpha-red' : 
                        data.bias === 'MIXED' ? 'bg-alpha-amber' : 'bg-slate-500'
                      )}
                      style={{ width: `${data.confidence}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Key Drivers */}
        <div>
          <h3 className="text-sm font-medium text-slate-400 mb-3">Key Market Drivers</h3>
          <div className="space-y-2">
            {outlook.drivers.map((driver, i) => (
              <div key={i} className="flex items-start gap-3 bg-slate-800/30 rounded-lg p-3">
                <div className="w-6 h-6 bg-alpha-blue/20 rounded-full flex items-center justify-center text-alpha-blue text-xs font-bold">
                  {i + 1}
                </div>
                <p className="text-sm text-slate-300 flex-1">{driver}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Outlook Summaries */}
        <div className="grid grid-cols-1 gap-4">
          <div className="bg-slate-800/50 rounded-lg p-4 border border-slate-700/50">
            <div className="flex items-center gap-2 mb-2">
              <svg className="w-4 h-4 text-alpha-cyan" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                <circle cx="12" cy="12" r="10"/>
                <polyline points="12 6 12 12 16 14"/>
              </svg>
              <h4 className="text-sm font-medium text-white">Short-Term Outlook</h4>
            </div>
            <p className="text-sm text-slate-400">{outlook.shortTermOutlook}</p>
          </div>
          <div className="bg-slate-800/50 rounded-lg p-4 border border-slate-700/50">
            <div className="flex items-center gap-2 mb-2">
              <svg className="w-4 h-4 text-alpha-purple" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>
                <line x1="16" y1="2" x2="16" y2="6"/>
                <line x1="8" y1="2" x2="8" y2="6"/>
                <line x1="3" y1="10" x2="21" y2="10"/>
              </svg>
              <h4 className="text-sm font-medium text-white">Session Outlook</h4>
            </div>
            <p className="text-sm text-slate-400">{outlook.sessionOutlook}</p>
          </div>
        </div>

        {/* Visual Bias Meter */}
        <div>
          <h3 className="text-sm font-medium text-slate-400 mb-3">Market Sentiment</h3>
          <div className="bg-slate-800/50 rounded-lg p-4 border border-slate-700/50">
            <div className="flex items-center justify-between mb-2 text-xs text-slate-500">
              <span>Bearish</span>
              <span>Neutral</span>
              <span>Bullish</span>
            </div>
            <div className="relative h-4 bg-gradient-to-r from-alpha-red via-slate-600 to-alpha-green rounded-full">
              <div
                className="absolute top-1/2 -translate-y-1/2 w-4 h-4 bg-white rounded-full shadow-lg border-2 border-slate-900 transition-all"
                style={{
                  left: `calc(${
                    outlook.overall === 'BULLISH' ? 75 + (outlook.confidence / 100) * 25 :
                    outlook.overall === 'BEARISH' ? 25 - (outlook.confidence / 100) * 25 :
                    50
                  }% - 8px)`
                }}
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
