import { ACTION_ORDER, ACTIONS, RISK_BAR } from "../actions.js";
import Panel from "./Panel.jsx";

export default function DecisionCard({ result, pending }) {
  if (!result) {
    return (
      <Panel title="Decision">
        <p className="text-sm text-slate-500">Simulating…</p>
      </Panel>
    );
  }
  const action = ACTIONS[result.action];
  return (
    <Panel
      title="Decision"
      aside={pending && <span className="text-xs text-slate-400">updating…</span>}
    >
      <div className={`rounded-lg px-4 py-3 text-white ${action.badge}`} aria-live="polite">
        <div className="text-2xl font-bold tracking-wide">{action.label}</div>
        <div className="text-sm opacity-90">{action.detail}</div>
      </div>

      <div>
        <div className="mb-1 flex items-baseline justify-between text-sm">
          <span className="font-medium text-slate-700">Route risk (Model 1)</span>
          <span className="tabular-nums">
            <span className="text-lg font-semibold">{result.risk_score.toFixed(2)}</span>{" "}
            <span className="text-xs text-slate-500">{result.risk_level}</span>
          </span>
        </div>
        <div className="relative h-3 rounded-full bg-slate-200">
          <div
            className={`h-3 rounded-full transition-all ${RISK_BAR[result.risk_level]}`}
            style={{ width: `${result.risk_score * 100}%` }}
          />
          <div
            className="absolute -top-1 h-5 w-0.5 bg-slate-900"
            style={{ left: `${result.threshold * 100}%` }}
            title={`Intervention threshold ${result.threshold}`}
          />
        </div>
        <div className="mt-1 text-right text-[11px] text-slate-500">
          threshold {result.threshold} · disaster {result.distance_ahead_km.toFixed(1)} km ahead
        </div>
      </div>

      {result.probabilities ? (
        <div>
          <div className="mb-1 text-sm font-medium text-slate-700">Action confidence (Model 2)</div>
          <div className="space-y-1">
            {ACTION_ORDER.map((key) => {
              const p = result.probabilities[key] ?? 0;
              return (
                <div key={key} className="flex items-center gap-2 text-xs">
                  <span className="w-24 shrink-0 text-slate-600">{ACTIONS[key].label}</span>
                  <div className="h-2 flex-1 rounded-full bg-slate-100">
                    <div className={`h-2 rounded-full ${ACTIONS[key].bar}`} style={{ width: `${p * 100}%` }} />
                  </div>
                  <span className="w-9 text-right tabular-nums">{Math.round(p * 100)}%</span>
                </div>
              );
            })}
          </div>
        </div>
      ) : (
        <p className="rounded-md bg-slate-50 px-3 py-2 text-xs text-slate-600">
          Risk is below the {result.threshold} threshold, so the decision gate was not crossed and Model 2 was not
          needed.
        </p>
      )}
    </Panel>
  );
}
