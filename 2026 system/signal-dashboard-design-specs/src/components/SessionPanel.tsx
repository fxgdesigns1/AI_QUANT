import { cn } from '../utils/cn';
import type { SessionState, RoadmapEvent } from '../types';

interface SessionPanelProps {
  session: SessionState;
  roadmap: RoadmapEvent[];
}

export function SessionPanel({ session, roadmap }: SessionPanelProps) {
  const sessionColors = {
    ASIA: 'from-alpha-purple to-indigo-600',
    LONDON: 'from-alpha-blue to-cyan-500',
    NEW_YORK: 'from-alpha-green to-emerald-500',
    OVERLAP_LN_NY: 'from-alpha-amber to-orange-500',
    OVERLAP_AS_LN: 'from-violet-500 to-fuchsia-500',
  };

  const gateConfig = {
    OPEN: { bg: 'bg-alpha-green/20', border: 'border-alpha-green/40', text: 'text-alpha-green', icon: '✓' },
    RESTRICTED: { bg: 'bg-alpha-amber/20', border: 'border-alpha-amber/40', text: 'text-alpha-amber', icon: '⚠' },
    CLOSED: { bg: 'bg-alpha-red/20', border: 'border-alpha-red/40', text: 'text-alpha-red', icon: '✕' },
  };

  const formatTimeUntil = (iso: string) => {
    const diff = new Date(iso).getTime() - Date.now();
    if (diff <= 0) return 'Now';
    const hours = Math.floor(diff / 3600000);
    const mins = Math.floor((diff % 3600000) / 60000);
    if (hours > 0) return `${hours}h ${mins}m`;
    return `${mins}m`;
  };

  const impactConfig = {
    LOW: { bg: 'bg-slate-600', text: 'text-slate-300' },
    MEDIUM: { bg: 'bg-alpha-amber/30', text: 'text-alpha-amber' },
    HIGH: { bg: 'bg-alpha-red/30', text: 'text-alpha-red' },
  };

  const eventTypeConfig = {
    NEWS: { icon: '📰', color: 'text-alpha-blue' },
    REGIME_RISK: { icon: '⚡', color: 'text-alpha-amber' },
    STRATEGY_SHIFT: { icon: '⟳', color: 'text-alpha-purple' },
    SYSTEM_NOTE: { icon: '📋', color: 'text-slate-400' },
  };

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-slate-800">
        <h2 className="text-lg font-semibold text-white">Session & Regime</h2>
        <p className="text-xs text-slate-500">Current market session and gate status</p>
      </div>

      <div className="flex-1 overflow-auto p-4 space-y-6">
        {/* Current Session Card */}
        <div className={cn('p-6 rounded-xl bg-gradient-to-br', sessionColors[session.current])}>
          <div className="flex items-center justify-between">
            <div>
              <div className="text-xs text-white/70 uppercase tracking-wider mb-1">Active Session</div>
              <div className="text-3xl font-bold text-white">{session.current.replace('_', ' ')}</div>
            </div>
            <div className="w-16 h-16 bg-white/20 rounded-full flex items-center justify-center">
              <svg className="w-8 h-8 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                <circle cx="12" cy="12" r="10"/>
                <path d="M12 6v6l4 2"/>
              </svg>
            </div>
          </div>
          <div className="mt-4 flex items-center gap-4 text-sm text-white/80">
            <div className="flex items-center gap-1">
              <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                <polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/>
              </svg>
              Next: {session.nextSession.replace('_', ' ')}
            </div>
            <div className="flex items-center gap-1">
              <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                <circle cx="12" cy="12" r="10"/>
                <polyline points="12 6 12 12 16 14"/>
              </svg>
              in {formatTimeUntil(session.nextTransition)}
            </div>
          </div>
        </div>

        {/* Gate Status */}
        <div>
          <h3 className="text-sm font-medium text-slate-400 mb-3">Session Gate</h3>
          <div className={cn('p-4 rounded-lg border', gateConfig[session.gateStatus].bg, gateConfig[session.gateStatus].border)}>
            <div className="flex items-center gap-3 mb-3">
              <div className={cn('text-2xl', gateConfig[session.gateStatus].text)}>
                {gateConfig[session.gateStatus].icon}
              </div>
              <div>
                <div className={cn('text-lg font-semibold', gateConfig[session.gateStatus].text)}>
                  {session.gateStatus}
                </div>
                <div className="text-xs text-slate-400">Trading gate status</div>
              </div>
            </div>
            <div className="bg-slate-900/50 rounded p-3">
              <div className="text-xs text-slate-500 uppercase tracking-wider mb-1">Gate Reasoning</div>
              <p className="text-sm text-slate-300">{session.gateReason}</p>
            </div>
          </div>
        </div>

        {/* Session Timeline */}
        <div>
          <h3 className="text-sm font-medium text-slate-400 mb-3">Session Timeline</h3>
          <div className="relative">
            <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
              <div className={cn('h-full bg-gradient-to-r', sessionColors[session.current])} style={{ width: '45%' }} />
            </div>
            <div className="flex justify-between mt-2 text-[10px] text-slate-500">
              <span>00:00</span>
              <span className="text-alpha-purple">Asia</span>
              <span className="text-alpha-blue">London</span>
              <span className="text-alpha-green">NY</span>
              <span>24:00</span>
            </div>
          </div>
        </div>

        {/* Upcoming Events / Roadmap */}
        <div>
          <h3 className="text-sm font-medium text-slate-400 mb-3">Upcoming Events</h3>
          <div className="space-y-2">
            {roadmap.map((event) => {
              const config = eventTypeConfig[event.type];
              const impact = impactConfig[event.impact];
              return (
                <div key={event.id} className="bg-slate-800/50 rounded-lg p-3 border border-slate-700/50">
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span className={cn('text-lg', config.color)}>{config.icon}</span>
                      <div>
                        <div className="text-sm font-medium text-white">{event.title}</div>
                        <div className="text-[10px] text-slate-500">{event.type.replace('_', ' ')}</div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={cn('px-1.5 py-0.5 rounded text-[10px] font-medium', impact.bg, impact.text)}>
                        {event.impact}
                      </span>
                      <span className="text-xs text-slate-400 font-mono">
                        {formatTimeUntil(event.timestamp)}
                      </span>
                    </div>
                  </div>
                  <p className="text-xs text-slate-400">{event.description}</p>
                </div>
              );
            })}
          </div>
        </div>

        {/* Market Closures */}
        {session.marketClosures.length > 0 && (
          <div>
            <h3 className="text-sm font-medium text-slate-400 mb-3">Upcoming Closures</h3>
            <div className="bg-alpha-amber/10 border border-alpha-amber/30 rounded-lg p-3">
              <div className="flex items-center gap-2 mb-2">
                <svg className="w-4 h-4 text-alpha-amber" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                  <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
                  <line x1="12" y1="9" x2="12" y2="13"/>
                  <line x1="12" y1="17" x2="12.01" y2="17"/>
                </svg>
                <span className="text-sm font-medium text-alpha-amber">Market Closures</span>
              </div>
              <ul className="space-y-1">
                {session.marketClosures.map((closure, i) => (
                  <li key={i} className="text-xs text-slate-300">{closure}</li>
                ))}
              </ul>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
