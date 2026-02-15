import { useCallback, useEffect, useMemo, useState } from "react";
import { LeftNav } from "./components/LeftNav";
import { TopBar } from "./components/TopBar";
import { ControlsPanel } from "./tabs/ControlsPanel";
import { SignalsPanel } from "./tabs/SignalsPanel";
import { JournalPanel } from "./tabs/JournalPanel";
import { OutlookPanel } from "./tabs/OutlookPanel";
import { NewsPanel } from "./tabs/NewsPanel";
import { MarketPanel } from "./tabs/MarketPanel";
import { ErrorsPanel } from "./tabs/ErrorsPanel";
import { PlaceholderPanel } from "./tabs/PlaceholderPanel";
import type { NavigationTab, StatusData, SystemHealth, MarketData, ErrorData } from "./types";
import { getJSON } from "../api/client";

import { SystemLogs } from "./components/SystemLogs";
import { RightPanel } from "./components/RightPanel";

function deriveHealthFromStatus(status: StatusData | undefined): SystemHealth {
  const systemAlive = Boolean(status?.system_alive);
  const mode = typeof status?.mode === "string" ? status.mode : null;
  const lastHeartbeat = (status?.last_status_write_at ?? status?.last_scan_at) as string | null;

  return {
    status: systemAlive ? "RUNNING" : "UNKNOWN",
    mode,
    cycleLatencyMs: null,
    lastHeartbeat: lastHeartbeat ?? null,
    version: null,
    safetyLock: "UNKNOWN",
    noTradeReason: status?.no_trade_reason,
    weekend: status?.weekend_indicator,
  };
}

type PanelState = "loading" | "error" | "empty" | "data";

function toPanelState(loading: boolean, error: string | null, data: unknown): PanelState {
  if (loading) return "loading";
  if (error) return "error";
  if (data == null) return "empty";
  const obj = data as Record<string, unknown>;
  const arr = Array.isArray(data) ? data : obj?.signals ?? obj?.trades ?? obj?.news ?? obj?.instruments ?? obj?.latest_events;
  if (Array.isArray(arr) && arr.length === 0) return "empty";
  if (typeof data === "object" && Object.keys(obj).length === 0) return "empty";
  return "data";
}

/** Normalize truth-wrapped response: use .data if present, else root. */
function unwrapData<T>(json: unknown): T {
  if (json != null && typeof json === "object" && "data" in json && (json as { data?: unknown }).data !== undefined) {
    return (json as { data: T }).data;
  }
  return json as T;
}

export function SignalDashboardShell() {
  const [activeTab, setActiveTab] = useState<NavigationTab>("signals");
  const [filters, setFilters] = useState({
    instrument: "All",
    strategy: "All",
    confidence: 0,
  });

  const [status, setStatus] = useState<StatusData | undefined>(undefined);
  const [statusError, setStatusError] = useState<string | null>(null);

  const [signalsLoading, setSignalsLoading] = useState(true);
  const [signalsError, setSignalsError] = useState<string | null>(null);
  const [signalsStatus, setSignalsStatus] = useState<number | undefined>(undefined);
  const [signalsData, setSignalsData] = useState<{ signals?: unknown[]; count?: number } | null>(null);

  const [journalLoading, setJournalLoading] = useState(true);
  const [journalError, setJournalError] = useState<string | null>(null);
  const [journalStatus, setJournalStatus] = useState<number | undefined>(undefined);
  const [journalData, setJournalData] = useState<{ trades?: unknown[]; total?: number } | null>(null);

  const [newsLoading, setNewsLoading] = useState(true);
  const [newsError, setNewsError] = useState<string | null>(null);
  const [newsStatus, setNewsStatus] = useState<number | undefined>(undefined);
  const [newsData, setNewsData] = useState<{ news?: unknown[] } | null>(null);

  const [outlookLoading, setOutlookLoading] = useState(true);
  const [outlookError, setOutlookError] = useState<string | null>(null);
  const [outlookStatus, setOutlookStatus] = useState<number | undefined>(undefined);
  const [outlookData, setOutlookData] = useState<Record<string, unknown> | null>(null);

  const [marketLoading, setMarketLoading] = useState(true);
  const [marketError, setMarketError] = useState<string | null>(null);
  const [marketStatus, setMarketStatus] = useState<number | undefined>(undefined);
  const [marketData, setMarketData] = useState<MarketData | null>(null);

  const [errorsLoading, setErrorsLoading] = useState(true);
  const [errorsError, setErrorsError] = useState<string | null>(null);
  const [errorsStatus, setErrorsStatus] = useState<number | undefined>(undefined);
  const [errorsData, setErrorsData] = useState<ErrorData | null>(null);

  const [selectedSignal, setSelectedSignal] = useState<Record<string, unknown> | null>(null);

  const loadStatus = useCallback(async () => {
    const r = await getJSON<StatusData>("/api/status", { timeoutMs: 10_000 });
    if (r.ok) {
      setStatus(unwrapData(r.data));
      setStatusError(null);
    } else {
      setStatusError(r.error || 'Unknown error');
    }
  }, []);

  const loadSignals = useCallback(async () => {
    setSignalsLoading(true);
    const r = await getJSON<{ signals?: unknown[]; count?: number }>("/api/signals?limit=100", { timeoutMs: 12_000 });
    setSignalsLoading(false);
    if (r.ok) {
      const raw = unwrapData<{ signals?: unknown[]; count?: number }>(r.data);
      const signals = Array.isArray(raw) ? raw : (raw?.signals ?? []);
      setSignalsData({ signals: Array.isArray(signals) ? signals : [], count: (raw as { count?: number })?.count });
      setSignalsError(null);
      setSignalsStatus(r.status);
    } else {
      setSignalsError(r.error || 'Unknown error');
      setSignalsStatus(r.status);
    }
  }, []);

  const loadJournal = useCallback(async () => {
    setJournalLoading(true);
    const r = await getJSON<{ trades?: unknown[]; total?: number }>("/api/journal/trades?limit=200&offset=0", {
      timeoutMs: 12_000,
    });
    setJournalLoading(false);
    if (r.ok) {
      const raw = unwrapData<{ trades?: unknown[]; total?: number }>(r.data);
      const trades = raw?.trades ?? (Array.isArray(raw) ? raw : []);
      setJournalData({ trades: Array.isArray(trades) ? trades : [], total: raw?.total ?? 0 });
      setJournalError(null);
      setJournalStatus(r.status);
    } else {
      setJournalError(r.error || 'Unknown error');
      setJournalStatus(r.status);
    }
  }, []);

  const loadNews = useCallback(async () => {
    setNewsLoading(true);
    const r = await getJSON<{ news?: unknown[] }>("/api/news", { timeoutMs: 12_000 });
    setNewsLoading(false);
    if (r.ok) {
      const raw = unwrapData<{ news?: unknown[] }>(r.data);
      const news = raw?.news ?? (Array.isArray(raw) ? raw : []);
      setNewsData({ news: Array.isArray(news) ? news : [] });
      setNewsError(null);
      setNewsStatus(r.status);
    } else {
      setNewsError(r.error || 'Unknown error');
      setNewsStatus(r.status);
    }
  }, []);

  const loadOutlook = useCallback(async () => {
    setOutlookLoading(true);
    const r = await getJSON<Record<string, unknown> | { outlook?: Record<string, unknown> }>("/api/v1/outlook/daily", {
      timeoutMs: 12_000,
    });
    setOutlookLoading(false);
    if (r.ok) {
      const raw = unwrapData<Record<string, unknown> | { outlook?: Record<string, unknown> }>(r.data);
      const outlook = raw && typeof raw === "object" && "outlook" in raw ? (raw as { outlook?: Record<string, unknown> }).outlook : (raw as Record<string, unknown>);
      setOutlookData(outlook ?? null);
      setOutlookError(null);
      setOutlookStatus(r.status);
    } else {
      setOutlookError(r.error || 'Unknown error');
      setOutlookStatus(r.status);
    }
  }, []);

  const loadMarket = useCallback(async () => {
    setMarketLoading(true);
    const r = await getJSON<MarketData>("/api/market/overview", { timeoutMs: 12_000 });
    setMarketLoading(false);
    if (r.ok) {
        const raw = unwrapData<MarketData>(r.data);
        setMarketData(raw);
        setMarketError(null);
        setMarketStatus(r.status);
    } else {
        setMarketError(r.error || 'Unknown error');
        setMarketStatus(r.status);
    }
  }, []);

  const loadErrors = useCallback(async () => {
      setErrorsLoading(true);
      // Fetch both errors and problems, merging if possible, but let's stick to /api/observability/problems for now as per P2 spec
      const r = await getJSON<ErrorData>("/api/observability/problems", { timeoutMs: 12_000 });
      setErrorsLoading(false);
      if (r.ok) {
          const raw = unwrapData<ErrorData>(r.data);
          setErrorsData(raw);
          setErrorsError(null);
          setErrorsStatus(r.status);
      } else {
          setErrorsError(r.error || 'Unknown error');
          setErrorsStatus(r.status);
      }
  }, []);

  useEffect(() => {
    loadStatus();
    const t = setInterval(loadStatus, 5_000);
    return () => clearInterval(t);
  }, [loadStatus]);

  useEffect(() => {
    loadSignals();
    loadJournal();
    loadNews();
    loadOutlook();
    loadMarket();
    loadErrors();
  }, [loadSignals, loadJournal, loadNews, loadOutlook, loadMarket, loadErrors]);

  const health = useMemo(() => deriveHealthFromStatus(status), [status]);

  const signalsState = toPanelState(
    signalsLoading,
    signalsError,
    signalsData?.signals?.length ? signalsData : signalsData?.signals
  );
  const journalState = toPanelState(journalLoading, journalError, journalData?.trades);
  const newsState = toPanelState(newsLoading, newsError, newsData?.news);
  const outlookState = toPanelState(outlookLoading, outlookError, outlookData);
  const marketState = toPanelState(marketLoading, marketError, marketData?.instruments);
  const errorsState = toPanelState(errorsLoading, errorsError, errorsData?.latest_events);

  const renderMainContent = () => {
    switch (activeTab) {
      case "controls":
        return <ControlsPanel />;

      case "signals":
        return (
          <SignalsPanel
            state={signalsState}
            error={signalsError}
            statusCode={signalsStatus}
            endpoint="/api/signals"
            signals={signalsData?.signals ?? []}
            filters={filters}
            selectedSignalId={selectedSignal?.id as string}
            onSelectSignal={(s) => setSelectedSignal(s as Record<string, unknown>)}
            onRetry={loadSignals}
          />
        );

      case "market":
        return (
            <MarketPanel 
                state={marketState}
                error={marketError}
                statusCode={marketStatus}
                endpoint="/api/market/overview"
                instruments={marketData?.instruments ?? []}
                ts_utc={marketData?.ts_utc}
                onRetry={loadMarket}
            />
        );

      case "journal":
        return (
          <JournalPanel
            state={journalState}
            error={journalError}
            statusCode={journalStatus}
            endpoint="/api/journal/trades"
            trades={journalData?.trades ?? []}
            total={journalData?.total}
            onRetry={loadJournal}
          />
        );

      case "outlook":
        return (
          <OutlookPanel
            state={outlookState}
            error={outlookError}
            statusCode={outlookStatus}
            endpoint="/api/v1/outlook/daily"
            outlook={outlookData}
            onRetry={loadOutlook}
          />
        );

      case "errors":
        return (
            <ErrorsPanel 
                state={errorsState}
                error={errorsError}
                statusCode={errorsStatus}
                data={errorsData}
                onRetry={loadErrors}
            />
        );

      case "strategy":
        return <PlaceholderPanel title="Strategy Health" subtitle="Per-strategy metrics" />;

      case "news":
        return (
          <NewsPanel
            state={newsState}
            error={newsError}
            statusCode={newsStatus}
            endpoint="/api/news"
            items={newsData?.news ?? []}
            onRetry={loadNews}
          />
        );

      default:
        return (
          <SignalsPanel
            state={signalsState}
            error={signalsError}
            statusCode={signalsStatus}
            endpoint="/api/signals"
            signals={signalsData?.signals ?? []}
            filters={filters}
            selectedSignalId={selectedSignal?.id as string}
            onSelectSignal={(s) => setSelectedSignal(s as Record<string, unknown>)}
            onRetry={loadSignals}
          />
        );
    }
  };

  return (
    <div className="h-screen flex flex-col bg-slate-950 text-slate-200 overflow-hidden">
      <TopBar health={health} newsCount={newsData?.news?.length ?? 0} />

      <div className="flex-1 flex overflow-hidden">
        <aside className="w-64 flex flex-col border-r border-slate-800 bg-slate-925">
          <LeftNav activeTab={activeTab} onTabChange={setActiveTab} filters={filters} onFilterChange={setFilters} />
          <SystemLogs />
        </aside>
        
        <main className="flex-1 flex overflow-hidden bg-slate-900/50">
          <div className="flex-1 flex flex-col overflow-hidden relative">
            {renderMainContent()}
          </div>
          
          {activeTab === "signals" && (
            <RightPanel selectedSignal={selectedSignal} />
          )}
        </main>
      </div>
    </div>
  );
}
