import { formatValue } from "../api.js";

export default function Slider({ def, value, onChange, format, auto = false, overridden = false, onReset }) {
  const shown = format ? format(value) : formatValue(value, def);
  const position = Math.min(Math.max(value, def.min), def.max);
  return (
    <div>
      <div className="flex items-center justify-between gap-2 text-sm">
        <span className="flex items-center gap-1.5 font-medium text-slate-700">
          {def.label}
          {auto && !overridden && (
            <span
              className="rounded bg-sky-100 px-1.5 py-px text-[10px] font-semibold tracking-wide text-sky-700 uppercase"
              title="Calculated from where the disaster is placed. Drag to override."
            >
              auto
            </span>
          )}
          {auto && overridden && (
            <button
              type="button"
              onClick={onReset}
              className="rounded bg-amber-100 px-1.5 py-px text-[10px] font-semibold tracking-wide text-amber-800 uppercase hover:bg-amber-200"
              title="You set this manually. Click to go back to the calculated value."
            >
              manual · reset
            </button>
          )}
        </span>
        <span className="text-slate-900 tabular-nums">{shown}</span>
      </div>
      <input
        type="range"
        aria-label={def.label}
        min={def.min}
        max={def.max}
        step={def.step}
        value={position}
        onChange={(e) => onChange(Number(e.target.value))}
        className="mt-1 w-full cursor-pointer accent-sky-600"
      />
    </div>
  );
}
