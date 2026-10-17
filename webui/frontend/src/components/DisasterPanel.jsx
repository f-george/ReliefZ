import Panel from "./Panel.jsx";
import Slider from "./Slider.jsx";

export default function DisasterPanel({ scenario, type, onTypeChange, disaster, onChange }) {
  const formats = {
    position_pct: (v) => `${v}% · ${((v / 100) * scenario.route_km).toFixed(1)} km`,
    severity: (v) => Number(v).toFixed(2),
    duration_min: (v) => (v >= 60 ? `${(v / 60).toFixed(v % 60 ? 1 : 0)} h` : `${v} min`),
  };
  return (
    <Panel title="Disaster">
      <div className="grid grid-cols-3 gap-1 rounded-lg bg-slate-100 p-1" role="radiogroup" aria-label="Disaster type">
        {Object.entries(scenario.disaster_types).map(([key, t]) => (
          <button
            key={key}
            type="button"
            role="radio"
            aria-checked={type === key}
            onClick={() => onTypeChange(key)}
            className={`flex items-center justify-center gap-1.5 rounded-md px-2 py-1.5 text-sm font-medium transition ${
              type === key ? "bg-white text-slate-900 shadow-sm" : "text-slate-500 hover:text-slate-800"
            }`}
          >
            <span className="size-2.5 shrink-0 rounded-full" style={{ backgroundColor: t.color }} />
            {t.short}
          </button>
        ))}
      </div>
      {scenario.disaster_sliders.map((def) => (
        <Slider
          key={def.key}
          def={def}
          value={disaster[def.key]}
          format={formats[def.key]}
          onChange={(v) => onChange(def.key, v)}
        />
      ))}
      <p className="text-xs text-slate-500">
        Position is measured along the convoy&apos;s planned {scenario.route_km} km route, starting from the convoy.
      </p>
    </Panel>
  );
}
