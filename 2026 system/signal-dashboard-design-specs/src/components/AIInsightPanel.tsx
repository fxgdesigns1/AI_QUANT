import { useState } from 'react';
import { cn } from '../utils/cn';
import type { AIProviderStatus } from '../types';

interface AIInsightPanelProps {
  aiProvider: AIProviderStatus;
}

const suggestedQuestions = [
  "Why is the EUR/USD signal confidence rising?",
  "Compare momentum vs mean reversion performance",
  "Summarize today's market outlook",
  "What's blocking AUD/USD signals?",
  "Explain the current regime detection",
  "Why are session gates restricted?",
];

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

export function AIInsightPanel({ aiProvider }: AIInsightPanelProps) {
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      role: 'assistant',
      content: "Hello! I'm your FXG ALPHA analytical co-pilot. I can help you understand system behavior, compare strategies, analyze signals, and answer questions about market conditions. Note: I have read-only access and cannot execute trades or modify configuration.",
      timestamp: new Date(),
    },
  ]);
  const [isThinking, setIsThinking] = useState(false);

  const handleSubmit = (query: string) => {
    if (!query.trim()) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: query,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsThinking(true);

    // Simulate AI response
    setTimeout(() => {
      const responses: Record<string, string> = {
        "Why is the EUR/USD signal confidence rising?": "The EUR/USD signal confidence is rising due to several converging factors:\n\n1. **Price Action**: Clean breakout above the 1.0850 resistance level with strong momentum\n2. **Volume Confirmation**: Above-average volume during the breakout suggests institutional participation\n3. **Regime Alignment**: Current TRENDING regime strongly favors momentum strategies\n4. **Session Quality**: We're in peak London session hours with optimal liquidity\n\nThe confidence trend shows +6% over the last 30 minutes, moving from 72% to 78%.",
        "Compare momentum vs mean reversion performance": "**Strategy Comparison (Last 30 Days)**\n\n📈 **MOMENTUM_BREAKOUT**\n• Win Rate: 72%\n• Avg R:R: 2.35\n• Signals: 47 generated, 8 blocked\n• Best in: TRENDING regime\n\n📉 **MEAN_REVERSION**\n• Win Rate: 65%\n• Avg R:R: 1.75\n• Signals: 38 generated, 12 blocked\n• Best in: RANGING regime\n\n**Recommendation**: Momentum strategies are currently outperforming given the prevailing TRENDING regime. Consider weighting momentum signals more heavily in the current environment.",
        "default": "Based on my analysis of the current system state:\n\nThe FXG ALPHA system is operating normally with 2 active signals and 1 forming. The London session is providing good liquidity conditions, and the overall market bias is BULLISH with 68% confidence.\n\nKey observations:\n• EUR/USD showing the strongest setup\n• USD/JPY restricted pending BoJ commentary\n• No high-impact news in the next 30 minutes\n\nIs there something specific you'd like me to analyze?",
      };

      const response = responses[query] || responses.default;

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: response,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, assistantMessage]);
      setIsThinking(false);
    }, 1500);
  };

  const healthConfig = {
    HEALTHY: { bg: 'bg-alpha-green/20', text: 'text-alpha-green' },
    DEGRADED: { bg: 'bg-alpha-amber/20', text: 'text-alpha-amber' },
    FAILED: { bg: 'bg-alpha-red/20', text: 'text-alpha-red' },
  };

  const aiConfig = healthConfig[aiProvider.health];

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-slate-800">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-white">AI Insight</h2>
            <p className="text-xs text-slate-500">Analytical co-pilot (read-only)</p>
          </div>
          <div className={cn('flex items-center gap-2 px-2 py-1 rounded', aiConfig.bg)}>
            <div className={cn('w-2 h-2 rounded-full', aiConfig.bg.replace('/20', ''))} />
            <span className={cn('text-xs font-medium', aiConfig.text)}>{aiProvider.active}</span>
          </div>
        </div>
      </div>

      {/* Read-only Notice */}
      <div className="px-4 py-2 bg-alpha-blue/10 border-b border-alpha-blue/20">
        <div className="flex items-center gap-2 text-xs text-alpha-blue">
          <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
            <circle cx="12" cy="12" r="10"/>
            <line x1="12" y1="16" x2="12" y2="12"/>
            <line x1="12" y1="8" x2="12.01" y2="8"/>
          </svg>
          <span>Read-only mode: Cannot execute trades, modify config, or restart service</span>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-auto p-4 space-y-4">
        {messages.map((message) => (
          <div
            key={message.id}
            className={cn(
              'max-w-[85%] rounded-xl p-4',
              message.role === 'user'
                ? 'ml-auto bg-alpha-blue text-white'
                : 'bg-slate-800/50 text-slate-200'
            )}
          >
            {message.role === 'assistant' && (
              <div className="flex items-center gap-2 mb-2">
                <div className="w-5 h-5 bg-alpha-purple/30 rounded flex items-center justify-center">
                  🤖
                </div>
                <span className="text-xs text-slate-400">FXG ALPHA AI</span>
              </div>
            )}
            <div className="text-sm whitespace-pre-wrap leading-relaxed">{message.content}</div>
            <div className={cn('text-[10px] mt-2', message.role === 'user' ? 'text-white/60' : 'text-slate-500')}>
              {message.timestamp.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })}
            </div>
          </div>
        ))}

        {isThinking && (
          <div className="bg-slate-800/50 rounded-xl p-4 max-w-[85%]">
            <div className="flex items-center gap-2 mb-2">
              <div className="w-5 h-5 bg-alpha-purple/30 rounded flex items-center justify-center">
                🤖
              </div>
              <span className="text-xs text-slate-400">FXG ALPHA AI</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="flex gap-1">
                <div className="w-2 h-2 bg-alpha-blue rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <div className="w-2 h-2 bg-alpha-blue rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <div className="w-2 h-2 bg-alpha-blue rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
              <span className="text-xs text-slate-400">Analyzing...</span>
            </div>
          </div>
        )}
      </div>

      {/* Suggested Questions */}
      <div className="px-4 py-2 border-t border-slate-800">
        <div className="text-[10px] text-slate-500 uppercase tracking-wider mb-2">Suggested</div>
        <div className="flex flex-wrap gap-2">
          {suggestedQuestions.slice(0, 3).map((q, i) => (
            <button
              key={i}
              onClick={() => handleSubmit(q)}
              className="px-2 py-1 bg-slate-800 hover:bg-slate-700 rounded text-xs text-slate-400 hover:text-white transition-colors"
            >
              {q}
            </button>
          ))}
        </div>
      </div>

      {/* Input */}
      <div className="p-4 border-t border-slate-800">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSubmit(input);
          }}
          className="flex items-center gap-2"
        >
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about signals, strategies, or market conditions..."
            className="flex-1 bg-slate-800 border border-slate-700 rounded-lg px-4 py-2.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-alpha-blue"
          />
          <button
            type="submit"
            disabled={!input.trim() || isThinking}
            className={cn(
              'px-4 py-2.5 rounded-lg text-sm font-medium transition-colors',
              input.trim() && !isThinking
                ? 'bg-alpha-blue text-white hover:bg-alpha-blue/80'
                : 'bg-slate-800 text-slate-500 cursor-not-allowed'
            )}
          >
            <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
              <line x1="22" y1="2" x2="11" y2="13"/>
              <polygon points="22 2 15 22 11 13 2 9 22 2"/>
            </svg>
          </button>
        </form>
      </div>
    </div>
  );
}
