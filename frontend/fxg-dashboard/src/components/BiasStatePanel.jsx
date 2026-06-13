import React, { useState, useEffect } from 'react';
import { apiGet } from '../api/client';

const REFRESH_RATE_MS = 5000;

export default function BiasStatePanel() {
  const [biasData, setBiasData] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchBias = async () => {
      try {
        const response = await apiGet('/api/observability/bias');
        if (response && response.data) {
          // Response structure: { data: { data: {...bias_states...}, ok: true, ... }, truth: {...} }
          const biasStates = response.data.data || {};
          setBiasData(biasStates);
          setError(null);
        }
      } catch (err) {
        // Silent fail on error, just log
        console.warn('Failed to fetch bias data:', err);
        // Don't set error state to avoid flashing error on UI, just show stale data or empty
      } finally {
        setLoading(false);
      }
    };

    fetchBias();
    const interval = setInterval(fetchBias, REFRESH_RATE_MS);
    return () => clearInterval(interval);
  }, []);

  const getBiasColor = (bias) => {
    switch(bias?.toLowerCase()) {
      case 'bullish': return 'text-green-400';
      case 'bearish': return 'text-red-400';
      case 'neutral': return 'text-yellow-400';
      default: return 'text-gray-500';
    }
  };
  
  const getStatusColor = (status) => {
      if (!status || status === 'unavailable') return 'text-gray-500';
      return getBiasColor(status);
  }

  if (loading) return <div className="p-4 bg-[#14161a] border border-[#2d2e35] rounded-lg text-gray-500 text-sm">Loading bias data...</div>;
  
  const instruments = Object.keys(biasData).sort();
  
  if (instruments.length === 0) {
      return (
        <div className="bg-[#14161a] border border-[#2d2e35] rounded-lg p-4">
            <h3 className="text-gray-400 text-sm font-bold uppercase tracking-wider mb-3 font-mono border-b border-[#2d2e35] pb-2">Bias Observability</h3>
            <div className="text-gray-500 text-center py-4 text-sm">Bias not yet observed</div>
        </div>
      );
  }

  return (
    <div className="bg-[#14161a] border border-[#2d2e35] rounded-lg p-4">
      <h3 className="text-gray-400 text-sm font-bold uppercase tracking-wider mb-3 font-mono border-b border-[#2d2e35] pb-2">Bias Observability</h3>
      <div className="space-y-3">
        {instruments.map(inst => {
          const data = biasData[inst];
          return (
            <div key={inst} className="bg-black/20 border border-[#2d2e35] rounded p-3">
              <div className="flex justify-between items-center mb-2">
                <div className="font-bold text-white text-sm">{inst}</div>
                <div className={`font-mono font-bold text-sm ${getBiasColor(data.final_bias)}`}>
                  {data.final_bias?.toUpperCase() || 'UNKNOWN'}
                </div>
              </div>
              
              <div className="grid grid-cols-3 gap-2 text-xs mb-2">
                <div className="bg-black/40 p-2 rounded">
                    <div className="text-gray-500 mb-1 text-[10px] uppercase">Price Action</div>
                    <div className={`font-mono ${getStatusColor(data.sources?.price_action?.status)}`}>
                        {data.sources?.price_action?.status?.toUpperCase() || 'N/A'}
                    </div>
                </div>
                 <div className="bg-black/40 p-2 rounded">
                    <div className="text-gray-500 mb-1 text-[10px] uppercase">Regime</div>
                    <div className={`font-mono ${getStatusColor(data.sources?.regime_bias?.status)}`}>
                        {data.sources?.regime_bias?.status?.toUpperCase() || 'N/A'}
                    </div>
                </div>
                 <div className="bg-black/40 p-2 rounded">
                    <div className="text-gray-500 mb-1 text-[10px] uppercase">Outlook</div>
                    <div className={`font-mono ${getStatusColor(data.sources?.outlook?.status)}`}>
                        {data.sources?.outlook?.status?.toUpperCase() || 'N/A'}
                    </div>
                </div>
              </div>
              
              {data.blocking_sources?.length > 0 && (
                  <div className="text-xs text-red-400 mt-2 bg-red-900/10 p-2 rounded border border-red-900/30">
                      <strong>Blocked by:</strong> {data.blocking_sources.join(', ')}
                  </div>
              )}
               <div className="text-[10px] text-gray-600 mt-1 text-right font-mono">
                  Regime: {data.regime}
               </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
