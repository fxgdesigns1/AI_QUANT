import { cn } from '../utils/cn';
import type { SystemHealth } from '../types';

interface TopBarProps {
  health: SystemHealth;
}

export function TopBar({ health }: TopBarProps) {
  const statusColors = {
    RUNNING: 'bg-alpha-green',
    STOPPED: 'bg-alpha-amber',
    ERROR: 'bg-alpha-red',
  };

  const formatUptime = (ms: number) => {
    const hours = Math.floor(ms / 3600000);
    const days = Math.floor(hours / 24);
    if (days > 0) return `${days}d ${hours % 24}h`;
    return `${hours}h`;
  };

  const formatTime = (iso: string) => {
    return new Date(iso).toLocaleTimeString('en-GB', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      timeZoneName: 'short',
    });
  };

  return (
    <header className="bg-slate-925 border-b border-slate-800 px-4 py-2.5">
      <div className="flex items-center justify-between">
        {/* Left: System Identity */}
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-gradient-to-br from-alpha-cyan to-alpha-blue rounded-lg flex items-center justify-center">
              <svg className="w-5 h-5 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                <path d="M3 3v18h18" strokeLinecap="round" strokeLinejoin="round"/>
                <path d="M18 9l-5-6-4 8-3-2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </div>
            <div>
              <h1 className="text-sm font-semibold text-white tracking-tight">FXG ALPHA</h1>
              <span className="text-[10px] text-slate-500 font-mono">v{health.version}</span>
            </div>
          </div>
          
          {/* Mode Badge */}
          <div className="px-2.5 py-1 bg-alpha-blue/20 border border-alpha-blue/30 rounded text-alpha-blue text-xs font-medium">
            {health.mode === 'PAPER' ? 'PAPER MODE' : 'SIGNAL SERVICE'}
          </div>
        </div>

        {/* Center: Status Indicators */}
        <div className="flex items-center gap-6">
          {/* Service Status */}
          <div className="flex items-center gap-2">
            <div className={cn('w-2 h-2 rounded-full', statusColors[health.status], health.status === 'RUNNING' && 'signal-pulse')} />
            <span className="text-xs text-slate-400">Service</span>
            <span className={cn('text-xs font-medium', health.status === 'RUNNING' ? 'text-alpha-green' : health.status === 'ERROR' ? 'text-alpha-red' : 'text-alpha-amber')}>
              {health.status}
            </span>
          </div>

          {/* Cycle Latency */}
          <div className="flex items-center gap-2">
            <svg className="w-3.5 h-3.5 text-slate-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
              <circle cx="12" cy="12" r="10"/>
              <polyline points="12 6 12 12 16 14"/>
            </svg>
            <span className="text-xs text-slate-400">Cycle</span>
            <span className={cn('text-xs font-mono font-medium', health.cycleLatencyMs < 200 ? 'text-alpha-green' : health.cycleLatencyMs < 500 ? 'text-alpha-amber' : 'text-alpha-red')}>
              {health.cycleLatencyMs}ms
            </span>
          </div>

          {/* Last Heartbeat */}
          <div className="flex items-center gap-2">
            <svg className="w-3.5 h-3.5 text-slate-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
              <path d="M22 12h-4l-3 9L9 3l-3 9H2"/>
            </svg>
            <span className="text-xs text-slate-400">Heartbeat</span>
            <span className="text-xs font-mono text-slate-300">{formatTime(health.lastHeartbeat)}</span>
          </div>

          {/* Uptime */}
          <div className="flex items-center gap-2">
            <svg className="w-3.5 h-3.5 text-slate-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
              <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>
              <line x1="16" y1="2" x2="16" y2="6"/>
              <line x1="8" y1="2" x2="8" y2="6"/>
              <line x1="3" y1="10" x2="21" y2="10"/>
            </svg>
            <span className="text-xs text-slate-400">Uptime</span>
            <span className="text-xs font-mono text-slate-300">{formatUptime(health.uptime)}</span>
          </div>
        </div>

        {/* Right: Safety Lock */}
        <div className="flex items-center gap-3">
          <div className={cn(
            'flex items-center gap-2 px-3 py-1.5 rounded border',
            health.tripleLockActive 
              ? 'bg-alpha-green/10 border-alpha-green/30' 
              : 'bg-alpha-red/10 border-alpha-red/30'
          )}>
            <div className="flex gap-0.5">
              {[1, 2, 3].map((i) => (
                <svg key={i} className={cn('w-3.5 h-3.5', health.tripleLockActive ? 'text-alpha-green' : 'text-alpha-red')} viewBox="0 0 24 24" fill="currentColor">
                  <path d="M12 2C9.24 2 7 4.24 7 7v3H6a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8a2 2 0 0 0-2-2h-1V7c0-2.76-2.24-5-5-5zm0 2c1.66 0 3 1.34 3 3v3H9V7c0-1.66 1.34-3 3-3z"/>
                </svg>
              ))}
            </div>
            <span className={cn('text-xs font-medium', health.tripleLockActive ? 'text-alpha-green' : 'text-alpha-red')}>
              {health.tripleLockActive ? 'LOCKED' : 'UNLOCKED'}
            </span>
          </div>
        </div>
      </div>
    </header>
  );
}
