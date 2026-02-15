interface PlaceholderPanelProps {
  title: string;
  subtitle?: string;
  extra?: React.ReactNode;
}

/**
 * Session, Strategy, System, AI: stub panel until backend endpoints are wired.
 * No mock data; explicit "Coming online" message.
 */
export function PlaceholderPanel({ title, subtitle, extra }: PlaceholderPanelProps) {
  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      <div className="px-4 py-3 border-b border-slate-800">
        <h2 className="text-lg font-semibold text-white">{title}</h2>
        {subtitle && <p className="text-xs text-slate-500">{subtitle}</p>}
      </div>
      <div className="flex-1 overflow-auto p-4">
        <div className="rounded-xl border border-slate-800 bg-slate-925 p-6">
          <p className="text-sm text-slate-300 font-medium mb-2">Coming online</p>
          <p className="text-xs text-slate-400">
            This panel will be wired only to real backend endpoints. No mock or demo data will ship.
          </p>
          {extra && <div className="mt-4">{extra}</div>}
        </div>
      </div>
    </div>
  );
}
