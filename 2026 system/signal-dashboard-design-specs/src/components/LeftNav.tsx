import { cn } from '../utils/cn';
import type { NavigationTab } from '../types';

interface LeftNavProps {
  activeTab: NavigationTab;
  onTabChange: (tab: NavigationTab) => void;
  filters: {
    instrument: string;
    strategy: string;
    confidence: number;
  };
  onFilterChange: (filters: { instrument: string; strategy: string; confidence: number }) => void;
}

const navItems: { id: NavigationTab; label: string; icon: React.ReactNode }[] = [
  {
    id: 'signals',
    label: 'Signals',
    icon: (
      <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
        <path d="M22 12h-4l-3 9L9 3l-3 9H2"/>
      </svg>
    ),
  },
  {
    id: 'journal',
    label: 'Trade Journal',
    icon: (
      <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
        <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/>
        <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>
      </svg>
    ),
  },
  {
    id: 'session',
    label: 'Session & Regime',
    icon: (
      <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
        <circle cx="12" cy="12" r="10"/>
        <path d="M12 6v6l4 2"/>
      </svg>
    ),
  },
  {
    id: 'outlook',
    label: 'Market Outlook',
    icon: (
      <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
        <circle cx="12" cy="12" r="10"/>
        <path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20"/>
        <path d="M2 12h20"/>
      </svg>
    ),
  },
  {
    id: 'strategy',
    label: 'Strategy Health',
    icon: (
      <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
        <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
        <polyline points="22 4 12 14.01 9 11.01"/>
      </svg>
    ),
  },
  {
    id: 'system',
    label: 'System & Costs',
    icon: (
      <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
        <rect x="2" y="3" width="20" height="14" rx="2" ry="2"/>
        <line x1="8" y1="21" x2="16" y2="21"/>
        <line x1="12" y1="17" x2="12" y2="21"/>
      </svg>
    ),
  },
  {
    id: 'ai',
    label: 'AI Insight',
    icon: (
      <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
        <path d="M12 2a2 2 0 0 1 2 2c0 .74-.4 1.39-1 1.73V7h1a7 7 0 0 1 7 7h1a1 1 0 0 1 1 1v3a1 1 0 0 1-1 1h-1v1a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-1H2a1 1 0 0 1-1-1v-3a1 1 0 0 1 1-1h1a7 7 0 0 1 7-7h1V5.73c-.6-.34-1-.99-1-1.73a2 2 0 0 1 2-2"/>
        <circle cx="7.5" cy="14.5" r="1.5"/>
        <circle cx="16.5" cy="14.5" r="1.5"/>
      </svg>
    ),
  },
];

const instruments = ['All', 'EUR/USD', 'GBP/USD', 'USD/JPY', 'AUD/USD', 'USD/CAD', 'NZD/USD'];
const strategies = ['All', 'MOMENTUM_BREAKOUT', 'MEAN_REVERSION', 'TREND_FOLLOW'];

export function LeftNav({ activeTab, onTabChange, filters, onFilterChange }: LeftNavProps) {
  return (
    <nav className="w-56 bg-slate-925 border-r border-slate-800 flex flex-col">
      {/* Navigation Items */}
      <div className="flex-1 py-3 overflow-y-auto">
        <div className="px-3 mb-2">
          <span className="text-[10px] font-medium text-slate-500 uppercase tracking-wider">Navigation</span>
        </div>
        <ul className="space-y-0.5 px-2">
          {navItems.map((item) => (
            <li key={item.id}>
              <button
                onClick={() => onTabChange(item.id)}
                className={cn(
                  'w-full flex items-center gap-2.5 px-2.5 py-2 rounded-md text-sm transition-colors',
                  activeTab === item.id
                    ? 'bg-alpha-blue/20 text-alpha-blue'
                    : 'text-slate-400 hover:bg-slate-800 hover:text-slate-300'
                )}
              >
                {item.icon}
                <span>{item.label}</span>
              </button>
            </li>
          ))}
        </ul>
      </div>

      {/* Filters Section */}
      <div className="border-t border-slate-800 p-3 space-y-3">
        <div className="text-[10px] font-medium text-slate-500 uppercase tracking-wider">Filters</div>
        
        {/* Instrument Selector */}
        <div>
          <label className="block text-xs text-slate-400 mb-1">Instrument</label>
          <select
            value={filters.instrument}
            onChange={(e) => onFilterChange({ ...filters, instrument: e.target.value })}
            className="w-full bg-slate-800 border border-slate-700 rounded px-2 py-1.5 text-xs text-slate-300 focus:outline-none focus:border-alpha-blue"
          >
            {instruments.map((inst) => (
              <option key={inst} value={inst}>{inst}</option>
            ))}
          </select>
        </div>

        {/* Strategy Selector */}
        <div>
          <label className="block text-xs text-slate-400 mb-1">Strategy</label>
          <select
            value={filters.strategy}
            onChange={(e) => onFilterChange({ ...filters, strategy: e.target.value })}
            className="w-full bg-slate-800 border border-slate-700 rounded px-2 py-1.5 text-xs text-slate-300 focus:outline-none focus:border-alpha-blue"
          >
            {strategies.map((strat) => (
              <option key={strat} value={strat}>{strat}</option>
            ))}
          </select>
        </div>

        {/* Confidence Slider */}
        <div>
          <label className="block text-xs text-slate-400 mb-1">
            Min Confidence: <span className="text-slate-300 font-medium">{filters.confidence}%</span>
          </label>
          <input
            type="range"
            min="0"
            max="100"
            value={filters.confidence}
            onChange={(e) => onFilterChange({ ...filters, confidence: parseInt(e.target.value) })}
            className="w-full h-1.5 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-alpha-blue"
          />
        </div>
      </div>
    </nav>
  );
}
