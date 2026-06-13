import type {
  SystemHealth,
  Signal,
  TimelineEvent,
  SessionState,
  MarketOutlook,
  RoadmapEvent,
  Trade,
  StrategyHealth,
  APIUsage,
  APIUsageAggregate,
  AIProviderStatus,
  StratEvidence,
} from '../types';

export const mockSystemHealth: SystemHealth = {
  status: 'RUNNING',
  mode: 'PAPER',
  cycleLatencyMs: 142,
  lastHeartbeat: new Date().toISOString(),
  tripleLockActive: true,
  version: '2.4.1',
  uptime: 86400000,
};

export const mockSignals: Signal[] = [
  {
    id: 'SIG-001',
    instrument: 'EUR/USD',
    strategy: 'MOMENTUM_BREAKOUT',
    direction: 'LONG',
    status: 'CONFIRMED',
    confidence: 78,
    confidenceTrend: 'RISING',
    regime: 'TRENDING',
    sessionGate: 'OPEN',
    newsImpact: 'NONE',
    validityWindowEnd: new Date(Date.now() + 3600000).toISOString(),
    createdAt: new Date(Date.now() - 1800000).toISOString(),
    updatedAt: new Date().toISOString(),
    reasoning: 'Strong bullish momentum confirmed by RSI divergence and volume spike. Price broke above key resistance at 1.0850 with conviction.',
  },
  {
    id: 'SIG-002',
    instrument: 'GBP/USD',
    strategy: 'MEAN_REVERSION',
    direction: 'SHORT',
    status: 'FORMING',
    confidence: 62,
    confidenceTrend: 'STABLE',
    regime: 'RANGING',
    sessionGate: 'OPEN',
    newsImpact: 'LOW',
    validityWindowEnd: new Date(Date.now() + 7200000).toISOString(),
    createdAt: new Date(Date.now() - 900000).toISOString(),
    updatedAt: new Date().toISOString(),
    reasoning: 'Price extended to upper Bollinger Band in ranging market. Awaiting reversal confirmation. Session liquidity supports entry.',
  },
  {
    id: 'SIG-003',
    instrument: 'USD/JPY',
    strategy: 'TREND_FOLLOW',
    direction: 'LONG',
    status: 'FORMING',
    confidence: 55,
    confidenceTrend: 'RISING',
    regime: 'TRENDING',
    sessionGate: 'RESTRICTED',
    newsImpact: 'MEDIUM',
    validityWindowEnd: new Date(Date.now() + 5400000).toISOString(),
    createdAt: new Date(Date.now() - 600000).toISOString(),
    updatedAt: new Date().toISOString(),
    reasoning: 'Trend continuation setup forming. Session gate restricted pending Tokyo open liquidity. BoJ commentary expected.',
  },
  {
    id: 'SIG-004',
    instrument: 'AUD/USD',
    strategy: 'MOMENTUM_BREAKOUT',
    direction: 'SHORT',
    status: 'INVALIDATED',
    confidence: 34,
    confidenceTrend: 'FALLING',
    regime: 'VOLATILE',
    sessionGate: 'CLOSED',
    newsImpact: 'HIGH',
    validityWindowEnd: new Date(Date.now() - 1800000).toISOString(),
    createdAt: new Date(Date.now() - 7200000).toISOString(),
    updatedAt: new Date().toISOString(),
    reasoning: 'Signal invalidated due to RBA rate decision surprise. Volatility regime triggered protective block.',
  },
];

export const mockTimeline: TimelineEvent[] = [
  { id: 'TL-001', signalId: 'SIG-001', type: 'FORMATION', timestamp: new Date(Date.now() - 1800000).toISOString(), description: 'Signal formed on EUR/USD momentum breakout' },
  { id: 'TL-002', signalId: 'SIG-001', type: 'CONFIDENCE_CROSS', timestamp: new Date(Date.now() - 1200000).toISOString(), description: 'Confidence crossed 70% threshold', value: 72 },
  { id: 'TL-003', signalId: 'SIG-001', type: 'CONFIRMATION', timestamp: new Date(Date.now() - 600000).toISOString(), description: 'Signal confirmed at 78% confidence', value: 78 },
  { id: 'TL-004', signalId: 'SIG-002', type: 'FORMATION', timestamp: new Date(Date.now() - 900000).toISOString(), description: 'Mean reversion signal forming on GBP/USD' },
  { id: 'TL-005', signalId: 'SIG-003', type: 'FORMATION', timestamp: new Date(Date.now() - 600000).toISOString(), description: 'Trend follow signal detected on USD/JPY' },
  { id: 'TL-006', signalId: 'SIG-004', type: 'INVALIDATION', timestamp: new Date(Date.now() - 300000).toISOString(), description: 'AUD/USD signal invalidated by news impact' },
];

export const mockSessionState: SessionState = {
  current: 'LONDON',
  gateStatus: 'OPEN',
  gateReason: 'London session active with normal liquidity. No high-impact events in next 30 minutes.',
  nextTransition: new Date(Date.now() + 14400000).toISOString(),
  nextSession: 'OVERLAP_LN_NY',
  marketClosures: ['2024-12-25 (Christmas)', '2024-12-26 (Boxing Day UK)'],
};

export const mockMarketOutlook: MarketOutlook = {
  overall: 'BULLISH',
  confidence: 68,
  instruments: {
    'EUR/USD': { bias: 'BULLISH', confidence: 75 },
    'GBP/USD': { bias: 'NEUTRAL', confidence: 52 },
    'USD/JPY': { bias: 'BULLISH', confidence: 64 },
    'AUD/USD': { bias: 'BEARISH', confidence: 58 },
    'USD/CAD': { bias: 'NEUTRAL', confidence: 45 },
    'NZD/USD': { bias: 'BEARISH', confidence: 61 },
  },
  drivers: ['Dollar weakness on Fed pivot signals', 'Risk-on sentiment in equities', 'EUR strength from ECB hawkish stance'],
  shortTermOutlook: 'Expect continuation of USD weakness through European session. Key level at DXY 103.50.',
  sessionOutlook: 'London session should provide clarity on EUR direction. Watch 1.0880 resistance.',
};

export const mockRoadmap: RoadmapEvent[] = [
  { id: 'RM-001', type: 'NEWS', timestamp: new Date(Date.now() + 3600000).toISOString(), title: 'US CPI Release', impact: 'HIGH', description: 'Core CPI expected +0.3% MoM. Major volatility expected across USD pairs.' },
  { id: 'RM-002', type: 'NEWS', timestamp: new Date(Date.now() + 7200000).toISOString(), title: 'ECB Minutes', impact: 'MEDIUM', description: 'ECB meeting minutes may provide insight into future rate path.' },
  { id: 'RM-003', type: 'REGIME_RISK', timestamp: new Date(Date.now() + 10800000).toISOString(), title: 'NY Open Volatility', impact: 'MEDIUM', description: 'Expected regime shift to VOLATILE during NY open if CPI surprises.' },
  { id: 'RM-004', type: 'SYSTEM_NOTE', timestamp: new Date(Date.now() + 86400000).toISOString(), title: 'Scheduled Maintenance', impact: 'LOW', description: 'System maintenance window: 00:00-01:00 UTC.' },
];

export const mockTrades: Trade[] = [
  { id: 'TR-001', signalId: 'SIG-100', instrument: 'EUR/USD', strategy: 'MOMENTUM_BREAKOUT', account: 'PAPER_001', direction: 'LONG', entryTime: new Date(Date.now() - 86400000).toISOString(), exitTime: new Date(Date.now() - 82800000).toISOString(), entryPrice: 1.0845, exitPrice: 1.0892, pnl: 47, pnlPips: 47, riskReward: 2.35, confidence: 82, session: 'LONDON', regime: 'TRENDING', duration: 3600000, mae: -8, mfe: 52, spread: 0.8, commission: 0 },
  { id: 'TR-002', signalId: 'SIG-101', instrument: 'GBP/USD', strategy: 'MEAN_REVERSION', account: 'PAPER_001', direction: 'SHORT', entryTime: new Date(Date.now() - 172800000).toISOString(), exitTime: new Date(Date.now() - 169200000).toISOString(), entryPrice: 1.2720, exitPrice: 1.2685, pnl: 35, pnlPips: 35, riskReward: 1.75, confidence: 74, session: 'NEW_YORK', regime: 'RANGING', duration: 3600000, mae: -12, mfe: 42, spread: 1.2, commission: 0 },
  { id: 'TR-003', signalId: 'SIG-102', instrument: 'USD/JPY', strategy: 'TREND_FOLLOW', account: 'PAPER_001', direction: 'LONG', entryTime: new Date(Date.now() - 259200000).toISOString(), exitTime: new Date(Date.now() - 252000000).toISOString(), entryPrice: 149.50, exitPrice: 149.20, pnl: -30, pnlPips: -30, riskReward: -0.75, confidence: 68, session: 'ASIA', regime: 'VOLATILE', duration: 7200000, mae: -45, mfe: 15, spread: 1.0, commission: 0 },
  { id: 'TR-004', signalId: 'SIG-103', instrument: 'EUR/USD', strategy: 'MOMENTUM_BREAKOUT', account: 'PAPER_001', direction: 'LONG', entryTime: new Date(Date.now() - 345600000).toISOString(), exitTime: new Date(Date.now() - 338400000).toISOString(), entryPrice: 1.0780, exitPrice: 1.0825, pnl: 45, pnlPips: 45, riskReward: 2.25, confidence: 79, session: 'OVERLAP_LN_NY', regime: 'TRENDING', duration: 7200000, mae: -5, mfe: 48, spread: 0.8, commission: 0 },
  { id: 'TR-005', signalId: 'SIG-104', instrument: 'AUD/USD', strategy: 'MEAN_REVERSION', account: 'PAPER_001', direction: 'LONG', entryTime: new Date(Date.now() - 432000000).toISOString(), exitTime: new Date(Date.now() - 428400000).toISOString(), entryPrice: 0.6520, exitPrice: 0.6555, pnl: 35, pnlPips: 35, riskReward: 1.4, confidence: 71, session: 'ASIA', regime: 'RANGING', duration: 3600000, mae: -10, mfe: 38, spread: 1.1, commission: 0 },
  { id: 'TR-006', signalId: 'SIG-105', instrument: 'USD/CAD', strategy: 'TREND_FOLLOW', account: 'PAPER_001', direction: 'SHORT', entryTime: new Date(Date.now() - 518400000).toISOString(), exitTime: new Date(Date.now() - 511200000).toISOString(), entryPrice: 1.3580, exitPrice: 1.3620, pnl: -40, pnlPips: -40, riskReward: -1.0, confidence: 65, session: 'NEW_YORK', regime: 'TRENDING', duration: 7200000, mae: -55, mfe: 12, spread: 1.5, commission: 0 },
  { id: 'TR-007', signalId: 'SIG-106', instrument: 'GBP/USD', strategy: 'MOMENTUM_BREAKOUT', account: 'PAPER_001', direction: 'LONG', entryTime: new Date(Date.now() - 604800000).toISOString(), exitTime: new Date(Date.now() - 597600000).toISOString(), entryPrice: 1.2650, exitPrice: 1.2710, pnl: 60, pnlPips: 60, riskReward: 3.0, confidence: 85, session: 'LONDON', regime: 'TRENDING', duration: 7200000, mae: -3, mfe: 65, spread: 1.2, commission: 0 },
  { id: 'TR-008', signalId: 'SIG-107', instrument: 'EUR/USD', strategy: 'MEAN_REVERSION', account: 'PAPER_001', direction: 'SHORT', entryTime: new Date(Date.now() - 691200000).toISOString(), exitTime: new Date(Date.now() - 687600000).toISOString(), entryPrice: 1.0920, exitPrice: 1.0880, pnl: 40, pnlPips: 40, riskReward: 2.0, confidence: 76, session: 'OVERLAP_LN_NY', regime: 'RANGING', duration: 3600000, mae: -8, mfe: 45, spread: 0.8, commission: 0 },
];

export const mockStrategyHealth: StrategyHealth[] = [
  { id: 'STRAT-001', name: 'MOMENTUM_BREAKOUT', signalsGenerated: 47, signalsBlocked: 8, tradesExecuted: 39, winRate: 72, avgConfidence: 76, regimeAlignment: 85, status: 'HEALTHY' },
  { id: 'STRAT-002', name: 'MEAN_REVERSION', signalsGenerated: 38, signalsBlocked: 12, tradesExecuted: 26, winRate: 65, avgConfidence: 68, regimeAlignment: 78, status: 'HEALTHY' },
  { id: 'STRAT-003', name: 'TREND_FOLLOW', signalsGenerated: 52, signalsBlocked: 15, tradesExecuted: 37, winRate: 58, avgConfidence: 64, regimeAlignment: 72, status: 'DEGRADED' },
];

export const mockAPIUsage: APIUsage[] = [
  { provider: 'NewsAPI', endpoint: '/v2/everything', callsToday: 245, callsThisHour: 18, rateLimit: 500, remaining: 255, lastCall: new Date(Date.now() - 120000).toISOString(), lastError: null, signalsInfluenced: 12 },
  { provider: 'ForexFactory', endpoint: '/calendar', callsToday: 48, callsThisHour: 4, rateLimit: 100, remaining: 52, lastCall: new Date(Date.now() - 900000).toISOString(), lastError: null, signalsInfluenced: 8 },
  { provider: 'TradingView', endpoint: '/signals', callsToday: 892, callsThisHour: 72, rateLimit: 1000, remaining: 108, lastCall: new Date(Date.now() - 60000).toISOString(), lastError: null, signalsInfluenced: 45 },
];

export const mockAPIUsageAggregate: APIUsageAggregate = {
  totalNewsApiCalls: 293,
  signalsBlockedByNews: 4,
  costPressure: 'LOW',
};

export const mockAIProviderStatus: AIProviderStatus = {
  active: 'CHATGPT',
  health: 'HEALTHY',
  latencyMs: 856,
  lastSuccess: new Date(Date.now() - 180000).toISOString(),
  failureCount: 0,
};

export const mockStratEvidence: StratEvidence = {
  summary: 'System is currently in ACTIVE signal generation mode with favorable market conditions. EUR/USD showing strongest setup with high confidence breakout pattern. London session providing optimal liquidity.',
  biasContributions: {
    'Technical Analysis': 0.45,
    'Regime Detection': 0.25,
    'Session Context': 0.15,
    'News Sentiment': 0.10,
    'Volatility Filter': 0.05,
  },
  confidenceBreakdown: [
    { factor: 'Price Action', contribution: 28, reasoning: 'Clean breakout above resistance with strong momentum' },
    { factor: 'Volume Profile', contribution: 22, reasoning: 'Above-average volume confirms institutional participation' },
    { factor: 'Regime Alignment', contribution: 18, reasoning: 'Trending regime favors momentum strategies' },
    { factor: 'Session Quality', contribution: 15, reasoning: 'London session peak liquidity hours' },
    { factor: 'Risk Metrics', contribution: 12, reasoning: 'Favorable risk/reward at current levels' },
  ],
  riskBlocks: [
    { reason: 'USD/JPY restricted pending BoJ commentary', severity: 'MEDIUM' },
    { reason: 'AUD/USD blocked due to high volatility regime', severity: 'HIGH' },
  ],
};
