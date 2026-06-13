import React, { useState, useEffect } from 'react';
import BiasConflictBadge from './BiasConflictBadge';
import { apiGet } from '../api/client';

const REFRESH_RATE_MS = 5000; // 5 seconds

/**
 * StrategyReadinessPanel - Shows readiness score and explanations per strategy
 * 
 * Displays:
 * - Readiness score with color bands (0-30 red, 31-60 amber, 61-80 blue, 81-100 green)
 * - Bias alignment badge
 * - "Why no trade yet" expandable section
 * - Estimated time to entry
 */
export default function StrategyReadinessPanel() {
  const [readinessData, setReadinessData] = useState(null);
  const [expandedStrategies, setExpandedStrategies] = useState(new Set());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchReadiness = async () => {
      try {
        const response = await apiGet('/api/readiness');
        if (!response || !response.data) {
          throw new Error('No data returned');
        }
        setReadinessData(response.data);
        setError(null);
      } catch (err) {
        setError(err.message);
        console.error('Failed to fetch readiness:', err);
      } finally {
        setLoading(false);
      }
    };

    // Initial fetch
    fetchReadiness();

    // Set up refresh interval
    const interval = setInterval(fetchReadiness, REFRESH_RATE_MS);

    return () => clearInterval(interval);
  }, []);

  const toggleExpand = (key) => {
    const newExpanded = new Set(expandedStrategies);
    if (newExpanded.has(key)) {
      newExpanded.delete(key);
    } else {
      newExpanded.add(key);
    }
    setExpandedStrategies(newExpanded);
  };

  const getScoreColor = (score) => {
    if (score <= 30) return '#f44336'; // Red
    if (score <= 60) return '#ff9800'; // Amber
    if (score <= 80) return '#2196f3'; // Blue
    return '#4caf50'; // Green
  };

  const getScoreBand = (score) => {
    if (score <= 30) return 'CRITICAL';
    if (score <= 60) return 'BLOCKED';
    if (score <= 80) return 'WAITING';
    return 'READY';
  };

  if (loading) {
    return (
      <div className="bg-[#14161a] border border-[#2d2e35] rounded-lg p-4">
        <h3 className="text-gray-400 text-sm font-bold uppercase tracking-wider mb-3 font-mono border-b border-[#2d2e35] pb-2">Strategy Readiness</h3>
        <p className="text-gray-500">Loading...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-[#14161a] border border-[#2d2e35] rounded-lg p-4">
        <h3 className="text-gray-400 text-sm font-bold uppercase tracking-wider mb-3 font-mono border-b border-[#2d2e35] pb-2">Strategy Readiness</h3>
        <p className="text-red-400">Error: {error}</p>
      </div>
    );
  }

  if (error && error.includes('No data returned')) {
    return (
      <div className="bg-[#14161a] border border-[#2d2e35] rounded-lg p-4">
        <h3 className="text-gray-400 text-sm font-bold uppercase tracking-wider mb-3 font-mono border-b border-[#2d2e35] pb-2">Strategy Readiness</h3>
        <div className="p-10 text-center">
          <div className="text-red-400 font-bold text-lg mb-2">READINESS_FILE_MISSING</div>
          <div className="text-gray-500 text-sm">runtime/strategy_readiness.json not found or empty</div>
        </div>
      </div>
    );
  }

  if (!readinessData || !readinessData.strategies || Object.keys(readinessData.strategies).length === 0) {
    return (
      <div className="bg-[#14161a] border border-[#2d2e35] rounded-lg p-4">
        <h3 className="text-gray-400 text-sm font-bold uppercase tracking-wider mb-3 font-mono border-b border-[#2d2e35] pb-2">Strategy Readiness</h3>
        <div className="p-10 text-center">
          <div className="text-red-400 font-bold text-lg mb-2">READINESS_FILE_MISSING</div>
          <div className="text-gray-500 text-sm">No readiness data available yet</div>
        </div>
      </div>
    );
  }

  const strategies = readinessData.strategies;

  return (
    <div className="space-y-4">
      <div className="bg-[#14161a] border border-[#2d2e35] rounded-lg p-4">
        <h3 className="text-gray-400 text-sm font-bold uppercase tracking-wider mb-3 font-mono border-b border-[#2d2e35] pb-2">Strategy Readiness</h3>
        <p className="text-gray-500 text-sm mb-4">
          Last updated: {readinessData.timestamp ? new Date(readinessData.timestamp).toLocaleString() : 'Unknown'}
        </p>

        <div className="space-y-3">
          {Object.entries(strategies).map(([key, strategy]) => {
            const isExpanded = expandedStrategies.has(key);
            const score = strategy.readiness_score || 0;
            const scoreColor = getScoreColor(score);
            const scoreBand = getScoreBand(score);

            return (
              <div
                key={key}
                className="bg-black/20 border border-[#2d2e35] rounded-lg p-4 hover:border-gray-600 transition-colors"
              >
                <div className="flex justify-between items-center mb-3">
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <strong className="text-white">{strategy.strategy_id}</strong>
                      <span className="text-gray-500">• {strategy.instrument}</span>
                      <BiasConflictBadge
                        dailyBias={strategy.daily_bias}
                        weeklyBias={strategy.weekly_bias}
                      />
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    <div className="text-right">
                      <div
                        className="text-2xl font-bold font-mono"
                        style={{ color: scoreColor }}
                      >
                        {score}
                      </div>
                      <div className="text-xs text-gray-500 uppercase">
                        {scoreBand}
                      </div>
                    </div>
                    <div
                      className="w-16 h-16 rounded-full flex items-center justify-center"
                      style={{ backgroundColor: scoreColor, opacity: 0.2 }}
                    >
                      <span className="text-xl font-bold font-mono" style={{ color: scoreColor }}>
                        {score}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="text-sm text-gray-400 mb-3">
                  <div>
                    <strong>Bias Alignment:</strong> <span className="text-white">{strategy.bias_alignment}</span>
                  </div>
                  {strategy.estimated_time_to_entry_minutes !== null && (
                    <div>
                      <strong>Est. Time to Entry:</strong> <span className="text-white">{strategy.estimated_time_to_entry_minutes}m</span>
                    </div>
                  )}
                </div>

                <button
                  onClick={() => toggleExpand(key)}
                  className="w-full text-left px-3 py-2 bg-black/30 border border-[#2d2e35] rounded text-sm text-gray-300 hover:bg-black/40 hover:border-gray-600 transition-colors"
                >
                  {isExpanded ? '▼' : '▶'} Why no trade yet
                </button>

                {isExpanded && (
                  <div className="mt-3 p-3 bg-black/30 border border-[#2d2e35] rounded">
                    <div className="mb-3 text-sm">
                      <strong className="text-gray-300">Explanation:</strong>
                      <div className="text-gray-400 mt-1">{strategy.explanation || strategy.why_not_trading}</div>
                    </div>
                    {strategy.blocking_reasons && strategy.blocking_reasons.length > 0 && (
                      <div className="mb-3 text-sm">
                        <strong className="text-gray-300">Blocking Reasons:</strong>
                        <ul className="mt-1 ml-4 list-disc text-gray-400">
                          {strategy.blocking_reasons.map((reason, idx) => (
                            <li key={idx}>{reason}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                    <div className="text-xs text-gray-500 space-y-1">
                      <div>Regime: {strategy.regime}</div>
                      <div>Volatility: {strategy.volatility_pct?.toFixed(1)}%</div>
                      <div>Embargo: {strategy.embargo_active ? 'Active' : 'None'}</div>
                      <div>Execution: {strategy.execution_allowed ? 'Allowed' : 'Blocked'}</div>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
