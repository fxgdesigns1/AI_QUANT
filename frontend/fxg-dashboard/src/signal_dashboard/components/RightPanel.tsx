import { useState } from "react";
import { cn } from "../utils/cn";

interface RightPanelProps {
  selectedSignal: Record<string, unknown> | null;
}

export function RightPanel({ selectedSignal }: RightPanelProps) {
  const [activeTab, setActiveTab] = useState<"insight" | "evidence">("insight");

  if (!selectedSignal) {
    return (
      <div className="w-80 border-l border-slate-800 bg-slate-950 flex flex-col items-center justify-center p-6 text-center">
        <div className="w-12 h-12 rounded-full bg-slate-900 flex items-center justify-center mb-4">
          <svg className="w-6 h-6 text-slate-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
        <p className="text-sm text-slate-400 font-medium">Select a signal to view AI insights and evidence.</p>
      </div>
    );
  }

  const insight = (selectedSignal.ai_insight || selectedSignal.reasoning || "No detailed insight available.") as string;
  const evidence = (selectedSignal.evidence || selectedSignal.technical_data || {}) as Record<string, unknown>;

  return (
    <div className="w-80 border-l border-slate-800 bg-slate-950 flex flex-col overflow-hidden">
      <div className="flex border-b border-slate-800">
        <button
          onClick={() => setActiveTab("insight")}
          className={cn(
            "flex-1 py-3 text-xs font-medium uppercase tracking-wider transition-colors",
            activeTab === "insight"
              ? "text-alpha-blue border-b-2 border-alpha-blue bg-slate-900/50"
              : "text-slate-500 hover:text-slate-300 hover:bg-slate-900/30"
          )}
        >
          AI Insight
        </button>
        <button
          onClick={() => setActiveTab("evidence")}
          className={cn(
            "flex-1 py-3 text-xs font-medium uppercase tracking-wider transition-colors",
            activeTab === "evidence"
              ? "text-alpha-blue border-b-2 border-alpha-blue bg-slate-900/50"
              : "text-slate-500 hover:text-slate-300 hover:bg-slate-900/30"
          )}
        >
          Evidence
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        {activeTab === "insight" ? (
          <div className="prose prose-invert prose-sm">
            <h3 className="text-sm font-semibold text-white mb-2">Analysis</h3>
            <p className="text-sm text-slate-300 whitespace-pre-wrap leading-relaxed">{insight}</p>
            
            {selectedSignal.confidence != null && (
              <div className="mt-6 p-3 rounded bg-slate-900 border border-slate-800">
                <div className="text-xs text-slate-500 uppercase tracking-wider mb-1">Confidence Score</div>
                <div className="flex items-end gap-2">
                  <span className="text-2xl font-bold text-white">{String(selectedSignal.confidence)}%</span>
                  <div className="flex-1 h-2 bg-slate-800 rounded-full mb-1.5 overflow-hidden">
                    <div 
                      className="h-full bg-alpha-blue rounded-full" 
                      style={{ width: `${selectedSignal.confidence}%` }}
                    />
                  </div>
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="space-y-4">
            <h3 className="text-sm font-semibold text-white">Technical Evidence</h3>
            {Object.keys(evidence).length === 0 ? (
              <p className="text-sm text-slate-500 italic">No structured evidence data.</p>
            ) : (
              <div className="space-y-2">
                {Object.entries(evidence).map(([key, value]) => (
                  <div key={key} className="p-2 rounded bg-slate-900/50 border border-slate-800/50">
                    <div className="text-[10px] text-slate-500 uppercase tracking-wider mb-0.5">{key.replace(/_/g, ' ')}</div>
                    <div className="text-xs font-mono text-slate-200 break-all">
                      {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
