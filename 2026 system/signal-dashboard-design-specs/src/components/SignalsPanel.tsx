import { useState } from 'react';
import { cn } from '../utils/cn';
import { SignalCard } from './SignalCard';
import type { Signal, TimelineEvent } from '../types';

interface SignalsPanelProps {
  signals: Signal[];
  timeline: TimelineEvent[];
  filters: { instrument: string; strategy: string; confidence: number };
}

export function SignalsPanel({ signals, timeline, filters }: SignalsPanelProps) {
  const [selectedSignal, setSelectedSignal] = useState<Signal | null>(null);
  const [view, setView] = useState<'cards' | 'timeline'>('cards');

  const filteredSignals = signals.filter((s) => {
    if (filters.instrument !== 'All' && s.instrument !== filters.instrument) return false;
    if (filters.strategy !== 'All' && s.strategy !== filters.strategy) return false;
    if (s.confidence < filters.confidence) return false;
    return true;
  });

  const activeSignals = filteredSignals.filter((s) => s.status === 'CONFIRMED' || s.status === 'FORMING');
  const inactiveSignals = filteredSignals.filter((s) => s.status === 'INVALIDATED' || s.status === 'EXPIRED');

  const formatTime = (iso: string) => {
    const date = new Date(iso);
    return date.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });
  };

  const formatTimeAgo = (iso: string) => {
    const diff = Date.now() - new Date(iso).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 60) return `${mins}m ago`;
    const hours = Math.floor(mins / 60);
    return `${hours}h ${mins % 60}m ago`;
  };

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* Panel Header */}
      <div className="px-4 py-3 border-b border-slate-800 flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-white">Active Signals</h2>
          <p className="text-xs text-slate-500">
            {activeSignals.length} active • {inactiveSignals.length} inactive
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setView('cards')}
            className={cn(
              'px-3 py-1.5 rounded text-xs font-medium transition-colors',
              view === 'cards' ? 'bg-alpha-blue text-white' : 'bg-slate-800 text-slate-400 hover:text-white'
            )}
          >
            Cards
          </button>
          <button
            onClick={() => setView('timeline')}
            className={cn(
              'px-3 py-1.5 rounded text-xs font-medium transition-colors',
              view === 'timeline' ? 'bg-alpha-blue text-white' : 'bg-slate-800 text-slate-400 hover:text-white'
            )}
          >
            Timeline
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto p-4">
        {view === 'cards' ? (
          <div className="space-y-6">
            {/* Active Signals */}
            {activeSignals.length > 0 && (
              <div>
                <h3 className="text-sm font-medium text-slate-400 mb-3 flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-alpha-green signal-pulse" />
                  Active Signals
                </h3>
                <div className="grid gap-3">
                  {activeSignals.map((signal) => (
                    <SignalCard
                      key={signal.id}
                      signal={signal}
                      onClick={() => setSelectedSignal(signal)}
                    />
                  ))}
                </div>
              </div>
            )}

            {/* Inactive Signals */}
            {inactiveSignals.length > 0 && (
              <div>
                <h3 className="text-sm font-medium text-slate-500 mb-3">Inactive Signals</h3>
                <div className="grid gap-3 opacity-60">
                  {inactiveSignals.map((signal) => (
                    <SignalCard
                      key={signal.id}
                      signal={signal}
                      onClick={() => setSelectedSignal(signal)}
                    />
                  ))}
                </div>
              </div>
            )}

            {filteredSignals.length === 0 && (
              <div className="text-center py-12">
                <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-slate-800/50 flex items-center justify-center">
                  <svg className="w-8 h-8 text-slate-600" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                    <path d="M22 12h-4l-3 9L9 3l-3 9H2"/>
                  </svg>
                </div>
                <p className="text-slate-400 text-sm font-medium mb-1">No signals match your filters</p>
                <p className="text-slate-500 text-xs">Try adjusting your filter criteria</p>
              </div>
            )}
          </div>
        ) : (
          /* Timeline View */
          <div className="relative">
            <div className="absolute left-4 top-0 bottom-0 w-px bg-slate-700" />
            <div className="space-y-4">
              {timeline.map((event) => {
                const typeConfig = {
                  FORMATION: { icon: '◉', color: 'text-alpha-blue' },
                  CONFIDENCE_CROSS: { icon: '↑', color: 'text-alpha-green' },
                  REGIME_CHANGE: { icon: '⟳', color: 'text-alpha-purple' },
                  INVALIDATION: { icon: '✕', color: 'text-alpha-red' },
                  CONFIRMATION: { icon: '✓', color: 'text-alpha-green' },
                  EXPIRY: { icon: '○', color: 'text-slate-500' },
                };
                const config = typeConfig[event.type];

                return (
                  <div key={event.id} className="relative pl-10">
                    <div className={cn('absolute left-2.5 w-3 h-3 rounded-full bg-slate-900 border-2 flex items-center justify-center text-[8px]', config.color)}>
                      {config.icon}
                    </div>
                    <div className="bg-slate-800/50 rounded-lg p-3 border border-slate-700/50">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-xs font-medium text-slate-300">{event.type.replace('_', ' ')}</span>
                        <span className="text-[10px] text-slate-500 font-mono">{formatTimeAgo(event.timestamp)}</span>
                      </div>
                      <p className="text-xs text-slate-400">{event.description}</p>
                      {event.value !== undefined && (
                        <div className="mt-1 text-xs text-alpha-cyan font-mono">Value: {event.value}%</div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>

      {/* Signal Detail Modal */}
      {selectedSignal && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4" onClick={() => setSelectedSignal(null)}>
          <div className="bg-slate-900 rounded-xl border border-slate-700 max-w-lg w-full max-h-[80vh] overflow-auto" onClick={(e) => e.stopPropagation()}>
            <div className="p-4 border-b border-slate-800 flex items-center justify-between">
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-xl font-bold text-white">{selectedSignal.instrument}</span>
                  <span className={cn(
                    'px-2 py-0.5 rounded text-xs font-medium',
                    selectedSignal.direction === 'LONG' ? 'bg-alpha-green/20 text-alpha-green' : 'bg-alpha-red/20 text-alpha-red'
                  )}>
                    {selectedSignal.direction}
                  </span>
                </div>
                <span className="text-xs text-slate-500 font-mono">{selectedSignal.id}</span>
              </div>
              <button onClick={() => setSelectedSignal(null)} className="p-1 hover:bg-slate-800 rounded">
                <svg className="w-5 h-5 text-slate-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                  <path d="M18 6 6 18M6 6l12 12"/>
                </svg>
              </button>
            </div>
            <div className="p-4 space-y-4">
              <div>
                <h4 className="text-xs font-medium text-slate-500 uppercase mb-2">Confidence Analysis</h4>
                <div className="flex items-center gap-3 mb-2">
                  <div className="text-3xl font-bold text-white">{selectedSignal.confidence}%</div>
                  <div className={cn('text-sm', selectedSignal.confidenceTrend === 'RISING' ? 'text-alpha-green' : selectedSignal.confidenceTrend === 'FALLING' ? 'text-alpha-red' : 'text-slate-400')}>
                    {selectedSignal.confidenceTrend}
                  </div>
                </div>
                <div className="h-3 bg-slate-700 rounded-full overflow-hidden">
                  <div
                    className={cn(
                      'h-full rounded-full',
                      selectedSignal.confidence >= 70 ? 'bg-alpha-green' : selectedSignal.confidence >= 50 ? 'bg-alpha-amber' : 'bg-alpha-red'
                    )}
                    style={{ width: `${selectedSignal.confidence}%` }}
                  />
                </div>
              </div>
              
              <div className="grid grid-cols-2 gap-3">
                <div className="bg-slate-800/50 p-3 rounded-lg">
                  <span className="text-xs text-slate-500">Strategy</span>
                  <p className="text-sm text-slate-200 font-medium">{selectedSignal.strategy.replace(/_/g, ' ')}</p>
                </div>
                <div className="bg-slate-800/50 p-3 rounded-lg">
                  <span className="text-xs text-slate-500">Regime</span>
                  <p className="text-sm text-slate-200 font-medium">{selectedSignal.regime}</p>
                </div>
                <div className="bg-slate-800/50 p-3 rounded-lg">
                  <span className="text-xs text-slate-500">Session Gate</span>
                  <p className={cn('text-sm font-medium', selectedSignal.sessionGate === 'OPEN' ? 'text-alpha-green' : selectedSignal.sessionGate === 'RESTRICTED' ? 'text-alpha-amber' : 'text-alpha-red')}>
                    {selectedSignal.sessionGate}
                  </p>
                </div>
                <div className="bg-slate-800/50 p-3 rounded-lg">
                  <span className="text-xs text-slate-500">News Impact</span>
                  <p className={cn('text-sm font-medium', selectedSignal.newsImpact === 'HIGH' ? 'text-alpha-red' : selectedSignal.newsImpact === 'MEDIUM' ? 'text-alpha-amber' : 'text-slate-300')}>
                    {selectedSignal.newsImpact}
                  </p>
                </div>
              </div>

              <div>
                <h4 className="text-xs font-medium text-slate-500 uppercase mb-2">System Reasoning</h4>
                <p className="text-sm text-slate-300 leading-relaxed">{selectedSignal.reasoning}</p>
              </div>

              <div className="flex items-center justify-between pt-2 border-t border-slate-800 text-xs text-slate-500">
                <span>Created: {formatTime(selectedSignal.createdAt)}</span>
                <span>Updated: {formatTime(selectedSignal.updatedAt)}</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
