import React from 'react';

/**
 * BiasConflictBadge - Shows bias conflict when daily != weekly bias
 * 
 * Props:
 * - dailyBias: string (BULLISH, BEARISH, NEUTRAL)
 * - weeklyBias: string (BULLISH, BEARISH, NEUTRAL)
 * - showTooltip: boolean (default: true)
 */
export default function BiasConflictBadge({ dailyBias, weeklyBias, showTooltip = true }) {
  // Check if there's a conflict (both directional but different)
  const hasConflict = 
    dailyBias && weeklyBias &&
    dailyBias !== 'NEUTRAL' && weeklyBias !== 'NEUTRAL' &&
    dailyBias !== weeklyBias;

  if (!hasConflict) {
    return null;
  }

  const conflictText = `D: ${dailyBias} | W: ${weeklyBias}`;
  const tooltipText = 'Conflict blocks entries until resolved or overridden by strategy';

  return (
    <span
      className="bias-conflict-badge"
      title={showTooltip ? tooltipText : undefined}
      style={{
        display: 'inline-block',
        padding: '2px 8px',
        borderRadius: '4px',
        backgroundColor: '#ff9800',
        color: '#fff',
        fontSize: '0.75rem',
        fontWeight: 'bold',
        marginLeft: '8px',
        cursor: showTooltip ? 'help' : 'default'
      }}
    >
      ⚠️ {conflictText}
    </span>
  );
}
