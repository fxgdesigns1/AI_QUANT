import { useState, useEffect } from 'react';
import { TopBar } from './components/TopBar';
import { LeftNav } from './components/LeftNav';
import { SignalsPanel } from './components/SignalsPanel';
import { TradeJournalPanel } from './components/TradeJournalPanel';
import { SessionPanel } from './components/SessionPanel';
import { OutlookPanel } from './components/OutlookPanel';
import { StrategyHealthPanel } from './components/StrategyHealthPanel';
import { SystemPanel } from './components/SystemPanel';
import { AIInsightPanel } from './components/AIInsightPanel';
import { ExplanationPanel } from './components/ExplanationPanel';
import {
  mockSystemHealth,
  mockSignals,
  mockTimeline,
  mockSessionState,
  mockMarketOutlook,
  mockRoadmap,
  mockTrades,
  mockStrategyHealth,
  mockAPIUsage,
  mockAPIUsageAggregate,
  mockAIProviderStatus,
  mockStratEvidence,
} from './data/mockData';
import type { NavigationTab, SystemHealth } from './types';

export function App() {
  const [activeTab, setActiveTab] = useState<NavigationTab>('signals');
  const [filters, setFilters] = useState({
    instrument: 'All',
    strategy: 'All',
    confidence: 0,
  });
  const [health, setHealth] = useState<SystemHealth>(mockSystemHealth);

  // Simulate heartbeat updates
  useEffect(() => {
    const interval = setInterval(() => {
      setHealth((prev) => ({
        ...prev,
        lastHeartbeat: new Date().toISOString(),
        cycleLatencyMs: Math.floor(120 + Math.random() * 60),
      }));
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  const renderMainContent = () => {
    switch (activeTab) {
      case 'signals':
        return (
          <SignalsPanel
            signals={mockSignals}
            timeline={mockTimeline}
            filters={filters}
          />
        );
      case 'journal':
        return <TradeJournalPanel trades={mockTrades} />;
      case 'session':
        return <SessionPanel session={mockSessionState} roadmap={mockRoadmap} />;
      case 'outlook':
        return <OutlookPanel outlook={mockMarketOutlook} />;
      case 'strategy':
        return <StrategyHealthPanel strategies={mockStrategyHealth} />;
      case 'system':
        return (
          <SystemPanel
            apiUsage={mockAPIUsage}
            apiAggregate={mockAPIUsageAggregate}
            aiProvider={mockAIProviderStatus}
          />
        );
      case 'ai':
        return <AIInsightPanel aiProvider={mockAIProviderStatus} />;
      default:
        return null;
    }
  };

  // Determine if we should show the explanation panel
  const showExplanation = activeTab === 'signals' || activeTab === 'outlook';

  return (
    <div className="h-screen flex flex-col bg-slate-950 text-slate-200 overflow-hidden">
      {/* Top Bar */}
      <TopBar health={health} />

      {/* Main Layout */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Navigation */}
        <LeftNav
          activeTab={activeTab}
          onTabChange={setActiveTab}
          filters={filters}
          onFilterChange={setFilters}
        />

        {/* Main Content Area */}
        <main className="flex-1 flex overflow-hidden bg-slate-900/50">
          {renderMainContent()}
        </main>

        {/* Right Explanation Panel */}
        {showExplanation && <ExplanationPanel evidence={mockStratEvidence} />}
      </div>
    </div>
  );
}
