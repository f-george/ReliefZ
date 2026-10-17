import Panel from "./Panel.jsx";
import Slider from "./Slider.jsx";

const PRIORITY = ["Low", "Moderate", "Medium", "High", "Critical"];

export default function FactorPanel({ sliders, values, autoKeys, overrides, onChange, onReset }) {
  const groups = [...new Set(sliders.map((s) => s.group))];
  return (
    <Panel title="Risk factors">
      <p className="text-xs text-slate-500">
        These are the nine inputs to the risk model. <span className="font-semibold text-sky-700">Auto</span> values
        follow the disaster&apos;s placement; drag one to set it manually.
      </p>
      {groups.map((group) => (
        <div key={group} className="space-y-3">
          <h3 className="border-b border-slate-100 pb-1 text-xs font-semibold text-slate-400">{group}</h3>
          {sliders
            .filter((s) => s.group === group)
            .map((def) => (
              <Slider
                key={def.key}
                def={def}
                value={values[def.key]}
                format={def.key === "road_closure_nearby" ? (v) => (v ? "Yes" : "No") : undefined}
                auto={autoKeys.includes(def.key)}
                overridden={overrides.includes(def.key)}
                onChange={(v) => onChange(def.key, v)}
                onReset={() => onReset(def.key)}
              />
            ))}
        </div>
      ))}
    </Panel>
  );
}

export function CargoPanel({ def, priority, onPriorityChange, hubAvailable, onHubChange }) {
  return (
    <Panel title="Cargo & logistics">
      <Slider
        def={def}
        value={priority}
        format={(v) => `${PRIORITY[v - 1]} (${v})`}
        onChange={onPriorityChange}
      />
      <label className="flex cursor-pointer items-center justify-between gap-3 text-sm font-medium text-slate-700">
        Backup hub available
        <input
          type="checkbox"
          checked={hubAvailable}
          onChange={(e) => onHubChange(e.target.checked)}
          className="peer sr-only"
        />
        <span className="relative h-5 w-9 rounded-full bg-slate-300 transition peer-checked:bg-sky-600 peer-focus-visible:ring-2 peer-focus-visible:ring-sky-400 after:absolute after:top-0.5 after:left-0.5 after:size-4 after:rounded-full after:bg-white after:transition peer-checked:after:translate-x-4" />
      </label>
    </Panel>
  );
}
