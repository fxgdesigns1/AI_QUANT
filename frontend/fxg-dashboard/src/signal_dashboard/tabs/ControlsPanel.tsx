import ControlPlaneMvp from "../../components/ControlPlaneMvp";

/**
 * Controls tab: embeds existing ControlPlaneMvp in a design container.
 * No logic changes to ControlPlaneMvp; token-gated patch remains optional.
 */
export function ControlsPanel() {
  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      <div className="px-4 py-3 border-b border-slate-800">
        <h2 className="text-lg font-semibold text-white">Controls</h2>
        <p className="text-xs text-slate-500">Status, schema, command pack, and config patch (token-gated)</p>
      </div>
      <div className="flex-1 overflow-auto p-4">
        <div className="rounded-xl border border-slate-800 bg-slate-925 p-4">
          <ControlPlaneMvp embedded />
        </div>
      </div>
    </div>
  );
}
