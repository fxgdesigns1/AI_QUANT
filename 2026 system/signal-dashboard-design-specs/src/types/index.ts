// Core Types for FXG ALPHA Dashboard

export type RunnerStatus = 'RUNNING' | 'STOPPED' | 'ERROR';
export type SignalDirection = 'LONG' | 'SHORT';
export type SignalStatus = 'FORMING' | 'CONFIRMED' | 'INVALIDATED' | 'EXPIRED';
export type Session = 'ASIA' | 'LONDON' | 'NEW_YORK' | 'OVERLAP_LN_NY' | 'OVERLAP_AS_LN';
export type GateStatus = 'OPEN' | 'RESTRICTED' | 'CLOSED';
export type Regime = 'TRENDING' | 'RANGING' | 'VOLATILE' | 'LOW_VOL' | 'UNKNOWN';
export type Bias = 'BULLISH' | 'BEARISH' | 'NEUTRAL' | 'MIXED';
export type CostPressure = 'LOW' | 'MEDIUM' | 'HIGH';
export type AIProvider = 'CHATGPT' | 'GEMINI' | 'AUTO';

export interface SystemHealth {
  status: RunnerStatus;
  mode: 'PAPER' | 'SIGNAL_SERVICE';
  cycleLatencyMs: number;
  lastHeartbeat: string;
  tripleLockActive: boolean;
  version: string;
  uptime: number;
}

export interface Signal {
  id: string;
  instrument: string;
  strategy: string;
  direction: SignalDirection;
  status: SignalStatus;
  confidence: number;
  confidenceTrend: 'RISING' | 'FALLING' | 'STABLE';
  regime: Regime;
  sessionGate: GateStatus;
  newsImpact: 'NONE' | 'LOW' | 'MEDIUM' | 'HIGH';
  validityWindowEnd: string;
  createdAt: string;
  updatedAt: string;
  reasoning: string;
}

export interface TimelineEvent {
  id: string;
  signalId: string;
  type: 'FORMATION' | 'CONFIDENCE_CROSS' | 'REGIME_CHANGE' | 'INVALIDATION' | 'CONFIRMATION' | 'EXPIRY';
  timestamp: string;
  description: string;
  value?: number;
}

export interface SessionState {
  current: Session;
  gateStatus: GateStatus;
  gateReason: string;
  nextTransition: string;
  nextSession: Session;
  marketClosures: string[];
}

export interface MarketOutlook {
  overall: Bias;
  confidence: number;
  instruments: Record<string, { bias: Bias; confidence: number }>;
  drivers: string[];
  shortTermOutlook: string;
  sessionOutlook: string;
}

export interface RoadmapEvent {
  id: string;
  type: 'NEWS' | 'REGIME_RISK' | 'STRATEGY_SHIFT' | 'SYSTEM_NOTE';
  timestamp: string;
  title: string;
  impact: 'LOW' | 'MEDIUM' | 'HIGH';
  description: string;
}

export interface Trade {
  id: string;
  signalId: string;
  instrument: string;
  strategy: string;
  account: string;
  direction: SignalDirection;
  entryTime: string;
  exitTime: string;
  entryPrice: number;
  exitPrice: number;
  pnl: number;
  pnlPips: number;
  riskReward: number;
  confidence: number;
  session: Session;
  regime: Regime;
  duration: number;
  mae: number;
  mfe: number;
  spread: number;
  commission: number;
}

export interface TradeStats {
  totalTrades: number;
  winRate: number;
  lossRate: number;
  avgRR: number;
  avgWin: number;
  avgLoss: number;
  expectancy: number;
  totalCost: number;
  avgDuration: number;
  avgMAE: number;
  avgMFE: number;
}

export interface StrategyHealth {
  id: string;
  name: string;
  signalsGenerated: number;
  signalsBlocked: number;
  tradesExecuted: number;
  winRate: number;
  avgConfidence: number;
  regimeAlignment: number;
  status: 'HEALTHY' | 'DEGRADED' | 'BLOCKED';
}

export interface APIUsage {
  provider: string;
  endpoint: string;
  callsToday: number;
  callsThisHour: number;
  rateLimit: number;
  remaining: number;
  lastCall: string;
  lastError: string | null;
  signalsInfluenced: number;
}

export interface APIUsageAggregate {
  totalNewsApiCalls: number;
  signalsBlockedByNews: number;
  costPressure: CostPressure;
}

export interface AIProviderStatus {
  active: AIProvider;
  health: 'HEALTHY' | 'DEGRADED' | 'FAILED';
  latencyMs: number;
  lastSuccess: string;
  failureCount: number;
}

export interface StratEvidence {
  summary: string;
  biasContributions: Record<string, number>;
  confidenceBreakdown: { factor: string; contribution: number; reasoning: string }[];
  riskBlocks: { reason: string; severity: 'LOW' | 'MEDIUM' | 'HIGH' }[];
  whyNoSignals?: string;
}

export type NavigationTab = 
  | 'signals' 
  | 'journal' 
  | 'session' 
  | 'outlook' 
  | 'strategy' 
  | 'system' 
  | 'ai';
