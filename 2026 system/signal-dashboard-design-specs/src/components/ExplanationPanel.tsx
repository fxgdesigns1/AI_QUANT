import { cn } from '../utils/cn';
import type { StratEvidence } from '../types';

interface ExplanationPanelProps {
  evidence: StratEvidence;
}

export function ExplanationPanel({ evidence }: ExplanationPanelProps) {
  const severityConfig = {
    LOW: { bg: 'bg-slate-600/30', text: 'text-slate-400' },
    MEDIUM: { bg: 'bg-alpha-amber/20', text: 'text-alpha-amber' },
    HIGH: { bg: 'bg-alpha-red/20', text: 'text-alpha-red' },
  };

  return (
    <aside className="w-80 bg-slate-925 border-l border-slate-800 flex flex-col overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-slate-800">
        <h3 className="text-sm font-semibold text-white">System Reasoning</h3>
        <p className="text-xs text-slate-500">Why the system is thinking this way</p>
      </div>

      <div className="flex-1 overflow-auto p-4 space-y-5">
        {/* Current Summary */}
        <div>
          <h4 className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-2">Current State</h4>
          <div className="bg-slate-800/50 rounded-lg p-3 border border-slate-700/50">
            <p className="text-sm text-slate-300 leading-relaxed">{evidence.summary}</p>
          </div>
        </div>

        {/* Bias Contributions */}
        <div>
          <h4 className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-2">Bias Sources</h4>
          <div className="space-y-2">
            {Object.entries(evidence.biasContributions).map(([source, weight]) => (
              <div key={source} className="bg-slate-800/30 rounded-lg p-2">
                <div className="flex items-center justify-between mb-1 text-xs">
                  <span className="text-slate-300">{source}</span>
                  <span className="text-alpha-cyan font-mono">{(weight * 100).toFixed(0)}%</span>
                </div>
                <div className="h-1.5 bg-slate-700 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-alpha-cyan rounded-full"
                    style={{ width: `${weight * 100}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Confidence Breakdown */}
        <div>
          <h4 className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-2">Confidence Factors</h4>
          <div className="space-y-2">
            {evidence.confidenceBreakdown.map((factor, i) => (
              <div key={i} className="bg-slate-800/30 rounded-lg p-3 border border-slate-700/50">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm font-medium text-white">{factor.factor}</span>
                  <span className={cn(
                    'text-xs font-mono px-1.5 py-0.5 rounded',
                    factor.contribution >= 20 ? 'bg-alpha-green/20 text-alpha-green' :
                    factor.contribution >= 10 ? 'bg-alpha-blue/20 text-alpha-blue' :
                    'bg-slate-600/30 text-slate-400'
                  )}>
                    +{factor.contribution}%
                  </span>
                </div>
                <p className="text-xs text-slate-400">{factor.reasoning}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Risk Blocks */}
        {evidence.riskBlocks.length > 0 && (
          <div>
            <h4 className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-2">Active Blocks</h4>
            <div className="space-y-2">
              {evidence.riskBlocks.map((block, i) => {
                const config = severityConfig[block.severity];
                return (
                  <div key={i} className={cn('rounded-lg p-3 border', config.bg, 'border-current/30')}>
                    <div className="flex items-start gap-2">
                      <svg className={cn('w-4 h-4 mt-0.5', config.text)} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                        <circle cx="12" cy="12" r="10"/>
                        <line x1="15" y1="9" x2="9" y2="15"/>
                        <line x1="9" y1="9" x2="15" y2="15"/>
                      </svg>
                      <div>
                        <div className={cn('text-xs font-medium mb-0.5', config.text)}>
                          {block.severity} SEVERITY
                        </div>
                        <p className="text-xs text-slate-300">{block.reason}</p>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Why No Signals */}
        {evidence.whyNoSignals && (
          <div>
            <h4 className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-2">Signal Absence</h4>
            <div className="bg-slate-800/30 rounded-lg p-3 border border-slate-600/50">
              <div className="flex items-start gap-2">
                <svg className="w-4 h-4 text-slate-400 mt-0.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                  <circle cx="12" cy="12" r="10"/>
                  <line x1="12" y1="16" x2="12" y2="12"/>
                  <line x1="12" y1="8" x2="12.01" y2="8"/>
                </svg>
                <p className="text-xs text-slate-400">{evidence.whyNoSignals}</p>
              </div>
            </div>
          </div>
        )}

        {/* Legend */}
        <div className="pt-4 border-t border-slate-800">
          <h4 className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-2">Understanding</h4>
          <div className="grid grid-cols-2 gap-2 text-[10px]">
            <div className="flex items-center gap-1.5">
              <div className="w-2 h-2 bg-alpha-green rounded-full" />
              <span className="text-slate-400">Strong Factor (20%+)</span>
            </div>
            <div className="flex items-center gap-1.5">
              <div className="w-2 h-2 bg-alpha-blue rounded-full" />
              <span className="text-slate-400">Moderate (10-20%)</span>
            </div>
            <div className="flex items-center gap-1.5">
              <div className="w-2 h-2 bg-slate-500 rounded-full" />
              <span className="text-slate-400">Minor (&lt;10%)</span>
            </div>
            <div className="flex items-center gap-1.5">
              <div className="w-2 h-2 bg-alpha-red rounded-full" />
              <span className="text-slate-400">Block Active</span>
            </div>
          </div>
        </div>
      </div>
    </aside>
  );
}
