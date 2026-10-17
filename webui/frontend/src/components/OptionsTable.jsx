import Panel from "./Panel.jsx";

function minutes(option) {
  if (option.minutes == null) return "—";
  const m = Math.round(option.minutes);
  return option.minutes_label === "to hub" ? `${m} min to hub` : `+${m} min`;
}

export default function OptionsTable({ result }) {
  if (!result) return null;
  return (
    <Panel title="Options compared">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-xs text-slate-500">
            <th className="pb-1 font-medium">Option</th>
            <th className="pb-1 text-right font-medium">Risk</th>
            <th className="pb-1 text-right font-medium">Time</th>
          </tr>
        </thead>
        <tbody>
          {result.options.map((o) => {
            const chosen = o.action === result.action;
            return (
              <tr key={o.action} className={`border-t border-slate-100 ${chosen ? "bg-sky-50 font-semibold" : ""}`}>
                <td className="py-1.5 pr-2">
                  {o.label}
                  {chosen && <span className="ml-1 text-sky-700">✓</span>}
                  <div className="text-[11px] font-normal text-slate-500">{o.note}</div>
                </td>
                <td className="py-1.5 text-right tabular-nums">{o.risk == null ? "—" : o.risk.toFixed(2)}</td>
                <td className="py-1.5 text-right tabular-nums">{minutes(o)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
      {!result.gate_crossed && (
        <p className="text-xs text-slate-500">
          Alternatives are only evaluated once risk crosses the threshold.
        </p>
      )}
    </Panel>
  );
}
