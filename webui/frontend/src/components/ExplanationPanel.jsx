import Panel from "./Panel.jsx";

function Chip({ children, className }) {
  return (
    <span className={`rounded px-1.5 py-px text-[10px] font-semibold tracking-wide uppercase ${className}`}>
      {children}
    </span>
  );
}

export default function ExplanationPanel({ result, granite, onExplain }) {
  if (!result) return null;
  const loading = granite.status === "loading";
  return (
    <Panel title="Explanation">
      <div>
        <Chip className="bg-slate-100 text-slate-600">Template</Chip>
        <p className="mt-1 text-sm leading-relaxed text-slate-700">{result.explanation}</p>
      </div>

      {granite.status === "done" && (
        <div className="rounded-md border border-sky-200 bg-sky-50 p-3">
          <Chip className="bg-sky-600 text-white">IBM Granite</Chip>
          <p className="mt-1 text-sm leading-relaxed text-slate-800">{granite.text}</p>
          <p className="mt-1 text-[11px] text-slate-500">
            {granite.source} · {granite.latency_s} s
          </p>
        </div>
      )}
      {granite.status === "error" && (
        <p className="rounded-md bg-amber-50 px-3 py-2 text-xs text-amber-800">
          Granite unavailable: {granite.error}. The template explanation above still applies.
        </p>
      )}

      <button
        type="button"
        onClick={onExplain}
        disabled={loading}
        className="w-full rounded-md bg-slate-900 px-3 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:cursor-wait disabled:opacity-60"
      >
        {loading ? "Granite is writing… (about 10–20 s)" : "Explain with Granite"}
      </button>
      <p className="text-[11px] text-slate-500">
        Granite runs locally with llama.cpp. It only explains the decision; it never changes it.
      </p>
    </Panel>
  );
}
