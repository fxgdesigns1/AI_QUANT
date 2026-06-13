import { cn } from '../utils/cn';
import type { APIUsage, APIUsageAggregate, AIProviderStatus } from '../types';

interface SystemPanelProps {
  apiUsage: APIUsage[];
  apiAggregate: APIUsageAggregate;
  aiProvider: AIProviderStatus;
}

export function SystemPanel({ apiUsage, apiAggregate, aiProvider }: SystemPanelProps) {
  const costPressureConfig = {
    LOW: { bg: 'bg-alpha-green/20', border: 'border-alpha-green/30', text: 'text-alpha-green' },
    MEDIUM: { bg: 'bg-alpha-amber/20', border: 'border-alpha-amber/30', text: 'text-alpha-amber' },
    HIGH: { bg: 'bg-alpha-red/20', border: 'border-alpha-red/30', text: 'text-alpha-red' },
  };

  const healthConfig = {
    HEALTHY: { bg: 'bg-alpha-green/20', text: 'text-alpha-green', icon: '✓' },
    DEGRADED: { bg: 'bg-alpha-amber/20', text: 'text-alpha-amber', icon: '⚠' },
    FAILED: { bg: 'bg-alpha-red/20', text: 'text-alpha-red', icon: '✕' },
  };

  const formatTime = (iso: string) => {
    return new Date(iso).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  };

  const cpConfig = costPressureConfig[apiAggregate.costPressure];
  const aiConfig = healthConfig[aiProvider.health];

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-slate-800">
        <h2 className="text-lg font-semibold text-white">System & Costs</h2>
        <p className="text-xs text-slate-500">API usage, costs, and AI provider status</p>
      </div>

      <div className="flex-1 overflow-auto p-4 space-y-6">
        {/* AI Provider Status */}
        <div>
          <h3 className="text-sm font-medium text-slate-400 mb-3">AI Provider</h3>
          <div className={cn('rounded-xl border p-4', aiConfig.bg, 'border-current/30')}>
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className={cn('w-12 h-12 rounded-lg flex items-center justify-center text-2xl', aiConfig.bg)}>
                  🤖
                </div>
                <div>
                  <h4 className="text-lg font-semibold text-white">{aiProvider.active}</h4>
                  <div className="flex items-center gap-2">
                    <span className={cn('text-xs font-medium', aiConfig.text)}>
                      {aiConfig.icon} {aiProvider.health}
                    </span>
                    <span className="text-xs text-slate-500">•</span>
                    <span className="text-xs text-slate-400">{aiProvider.latencyMs}ms latency</span>
                  </div>
                </div>
              </div>
              <div className="text-right">
                <div className="text-xs text-slate-500">Failure Count</div>
                <div className={cn('text-xl font-bold', aiProvider.failureCount === 0 ? 'text-alpha-green' : 'text-alpha-red')}>
                  {aiProvider.failureCount}
                </div>
              </div>
            </div>
            <div className="bg-slate-900/50 rounded-lg p-3 text-xs">
              <div className="flex items-center justify-between">
                <span className="text-slate-500">Last Success</span>
                <span className="text-slate-300 font-mono">{formatTime(aiProvider.lastSuccess)}</span>
              </div>
            </div>
            <div className="mt-3 p-3 bg-slate-800/30 rounded-lg border border-slate-700/50">
              <div className="flex items-center gap-2 text-xs text-slate-400">
                <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                  <circle cx="12" cy="12" r="10"/>
                  <line x1="12" y1="16" x2="12" y2="12"/>
                  <line x1="12" y1="8" x2="12.01" y2="8"/>
                </svg>
                <span>Provider changes require confirmation and service restart</span>
              </div>
            </div>
          </div>
        </div>

        {/* Cost Pressure Overview */}
        <div>
          <h3 className="text-sm font-medium text-slate-400 mb-3">Cost Overview</h3>
          <div className="grid grid-cols-3 gap-3">
            <div className="bg-slate-800/50 rounded-lg p-4 border border-slate-700/50">
              <div className="text-xs text-slate-500 mb-1">News API Calls</div>
              <div className="text-2xl font-bold text-white">{apiAggregate.totalNewsApiCalls}</div>
              <div className="text-xs text-slate-400">today</div>
            </div>
            <div className="bg-slate-800/50 rounded-lg p-4 border border-slate-700/50">
              <div className="text-xs text-slate-500 mb-1">Signals Blocked</div>
              <div className="text-2xl font-bold text-alpha-amber">{apiAggregate.signalsBlockedByNews}</div>
              <div className="text-xs text-slate-400">by news embargo</div>
            </div>
            <div className={cn('rounded-lg p-4 border', cpConfig.bg, cpConfig.border)}>
              <div className="text-xs text-slate-500 mb-1">Cost Pressure</div>
              <div className={cn('text-2xl font-bold', cpConfig.text)}>{apiAggregate.costPressure}</div>
              <div className="text-xs text-slate-400">current level</div>
            </div>
          </div>
        </div>

        {/* API Usage Table */}
        <div>
          <h3 className="text-sm font-medium text-slate-400 mb-3">API Usage Details</h3>
          <div className="bg-slate-800/30 rounded-lg border border-slate-700/50 overflow-hidden">
            <table className="w-full text-xs">
              <thead className="bg-slate-900/50">
                <tr className="text-left text-slate-500">
                  <th className="px-4 py-2.5 font-medium">Provider</th>
                  <th className="px-4 py-2.5 font-medium">Endpoint</th>
                  <th className="px-4 py-2.5 font-medium text-right">Today</th>
                  <th className="px-4 py-2.5 font-medium text-right">Hour</th>
                  <th className="px-4 py-2.5 font-medium text-right">Remaining</th>
                  <th className="px-4 py-2.5 font-medium text-right">Signals</th>
                  <th className="px-4 py-2.5 font-medium">Status</th>
                </tr>
              </thead>
              <tbody>
                {apiUsage.map((api, i) => {
                  const usagePercent = ((api.rateLimit - api.remaining) / api.rateLimit) * 100;
                  const isHigh = usagePercent > 80;
                  const isMedium = usagePercent > 50;
                  return (
                    <tr key={i} className="border-t border-slate-700/50">
                      <td className="px-4 py-3 text-slate-200 font-medium">{api.provider}</td>
                      <td className="px-4 py-3 text-slate-400 font-mono">{api.endpoint}</td>
                      <td className="px-4 py-3 text-right text-slate-300">{api.callsToday}</td>
                      <td className="px-4 py-3 text-right text-slate-300">{api.callsThisHour}</td>
                      <td className="px-4 py-3 text-right">
                        <span className={cn('font-mono', isHigh ? 'text-alpha-red' : isMedium ? 'text-alpha-amber' : 'text-alpha-green')}>
                          {api.remaining}/{api.rateLimit}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right text-alpha-blue">{api.signalsInfluenced}</td>
                      <td className="px-4 py-3">
                        {api.lastError ? (
                          <span className="px-2 py-0.5 bg-alpha-red/20 text-alpha-red rounded text-[10px]">ERROR</span>
                        ) : (
                          <span className="px-2 py-0.5 bg-alpha-green/20 text-alpha-green rounded text-[10px]">OK</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Usage Visualization */}
        <div>
          <h3 className="text-sm font-medium text-slate-400 mb-3">Rate Limit Usage</h3>
          <div className="space-y-3">
            {apiUsage.map((api, i) => {
              const usagePercent = ((api.rateLimit - api.remaining) / api.rateLimit) * 100;
              return (
                <div key={i} className="bg-slate-800/30 rounded-lg p-3">
                  <div className="flex items-center justify-between mb-2 text-xs">
                    <span className="text-slate-300 font-medium">{api.provider}</span>
                    <span className="text-slate-400">{usagePercent.toFixed(1)}% used</span>
                  </div>
                  <div className="h-2 bg-slate-700 rounded-full overflow-hidden">
                    <div
                      className={cn(
                        'h-full rounded-full transition-all',
                        usagePercent > 80 ? 'bg-alpha-red' : usagePercent > 50 ? 'bg-alpha-amber' : 'bg-alpha-green'
                      )}
                      style={{ width: `${usagePercent}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
