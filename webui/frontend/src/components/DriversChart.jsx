import Panel from "./Panel.jsx";

export default function DriversChart({ result }) {
  if (!result) return null;
  const drivers = result.risk_drivers;
  const max = Math.max(...drivers.map((d) => d.risk_drop), 0.01);
  return (
    <Panel title="What drives the risk">
      {drivers.length === 0 ? (
        <p className="text-sm text-slate-500">No single factor stands out.</p>
      ) : (
        <div className="space-y-1.5">
          {drivers.map((d) => (
            <div key={d.feature} className="text-xs">
              <div className="flex justify-between">
                <span className="text-slate-700 first-letter:uppercase">{d.label}</span>
                <span className="text-slate-500 tabular-nums">−{d.risk_drop.toFixed(2)}</span>
              </div>
              <div className="mt-0.5 h-2 rounded-full bg-slate-100">
                <div className="h-2 rounded-full bg-red-400" style={{ width: `${(d.risk_drop / max) * 100}%` }} />
              </div>
            </div>
          ))}
        </div>
      )}
      <p className="text-[11px] text-slate-500">How much the risk would drop if that factor alone returned to normal.</p>
    </Panel>
  );
}
