import { useEffect, useRef, useState } from "react";
import { getJSON, postJSON } from "./api.js";
import DecisionCard from "./components/DecisionCard.jsx";
import DisasterPanel from "./components/DisasterPanel.jsx";
import DriversChart from "./components/DriversChart.jsx";
import ExplanationPanel from "./components/ExplanationPanel.jsx";
import FactorPanel, { CargoPanel } from "./components/FactorPanel.jsx";
import MapView from "./components/MapView.jsx";
import OptionsTable from "./components/OptionsTable.jsx";

const defaultsOf = (sliders) => Object.fromEntries(sliders.map((s) => [s.key, s.default]));

export default function App() {
  const [scenario, setScenario] = useState(null);
  const [network, setNetwork] = useState(null);
  const [loadError, setLoadError] = useState(null);

  const [type, setType] = useState("flood");
  const [disaster, setDisaster] = useState({});
  const [factors, setFactors] = useState({});
  const [overrides, setOverrides] = useState([]);
  const [cargo, setCargo] = useState(5);
  const [hubAvailable, setHubAvailable] = useState(true);

  const [result, setResult] = useState(null);
  const [simError, setSimError] = useState(null);
  const [pending, setPending] = useState(false);
  const [granite, setGranite] = useState({ status: "idle" });
  const graniteRequest = useRef(0);

  useEffect(() => {
    getJSON("/api/scenario")
      .then((s) => {
        setScenario(s);
        setType(s.default_type);
        setDisaster(defaultsOf(s.disaster_sliders));
        setFactors(defaultsOf(s.factor_sliders));
        setCargo(s.cargo_slider.default);
      })
      .catch((e) => setLoadError(e.message));
    getJSON("/api/network")
      .then((n) => setNetwork(n.segments))
      .catch(() => {});
  }, []);

  // Re-simulate when any input changes: debounced, and stale requests are cancelled
  useEffect(() => {
    if (!scenario) return undefined;
    graniteRequest.current += 1; // any Granite answer in flight no longer matches the inputs
    setGranite({ status: "idle" });
    const controller = new AbortController();
    const timer = setTimeout(() => {
      setPending(true);
      postJSON(
        "/api/simulate",
        { type, disaster, factors, overrides, cargo_priority: cargo, backup_hub_available: hubAvailable },
        controller.signal,
      )
        .then((r) => {
          setResult(r);
          setSimError(null);
          setPending(false);
        })
        .catch((e) => {
          if (e.name === "AbortError") return;
          setSimError(e.message);
          setPending(false);
        });
    }, 150);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [scenario, type, disaster, factors, overrides, cargo, hubAvailable]);

  if (loadError) {
    return (
      <div className="m-8 rounded-lg bg-red-50 p-4 text-red-800">
        Could not load the scenario from the server: {loadError}. Is <code>webui/app.py</code> running?
      </div>
    );
  }
  if (!scenario) return <div className="m-8 text-slate-500">Loading scenario…</div>;

  const autoKeys = scenario.disaster_types[type].auto_factors;
  const factorValues = Object.fromEntries(
    Object.entries(factors).map(([k, v]) => [
      k,
      autoKeys.includes(k) && !overrides.includes(k) ? (result?.auto_factors?.[k] ?? v) : v,
    ]),
  );

  function changeType(next) {
    const preset = scenario.disaster_types[next];
    setType(next);
    setDisaster((d) => ({ ...d, ...preset.disaster }));
    setFactors((f) => ({ ...f, ...preset.factors }));
    setOverrides([]);
  }

  function changeFactor(key, value) {
    setFactors((f) => ({ ...f, [key]: value }));
    if (autoKeys.includes(key)) setOverrides((o) => (o.includes(key) ? o : [...o, key]));
  }

  function explain() {
    const id = ++graniteRequest.current;
    setGranite({ status: "loading" });
    postJSON("/api/explain", { facts: result.facts })
      .then((r) => id === graniteRequest.current && setGranite({ status: "done", ...r }))
      .catch((e) => id === graniteRequest.current && setGranite({ status: "error", error: e.message }));
  }

  return (
    <div className="flex min-h-screen flex-col lg:h-screen">
      <header className="flex flex-wrap items-center justify-between gap-2 bg-slate-900 px-4 py-2.5 text-white">
        <div>
          <h1 className="text-lg font-semibold">ReliefSync Z</h1>
          <p className="text-xs text-slate-300">Disaster convoy decision simulator</p>
        </div>
        <div className="flex flex-wrap items-center gap-2 text-[11px]">
          <span className="rounded bg-amber-400 px-2 py-0.5 font-semibold text-slate-900">Simulated data</span>
          <span className="rounded bg-slate-700 px-2 py-0.5">
            Running on {scenario.platform.machine} · Python {scenario.platform.python}
          </span>
          {result && <span className="rounded bg-slate-700 px-2 py-0.5 tabular-nums">{result.compute_ms} ms</span>}
        </div>
      </header>

      {simError && <div className="bg-red-50 px-4 py-2 text-sm text-red-800">Simulation failed: {simError}</div>}

      <main className="grid flex-1 grid-cols-1 lg:min-h-0 lg:grid-cols-[21rem_minmax(0,1fr)_24rem]">
        {/* On phones: map, then decision, then controls, so the result stays near the top */}
        <aside className="order-3 space-y-4 bg-slate-50 p-4 lg:order-1 lg:overflow-y-auto">
          <DisasterPanel
            scenario={scenario}
            type={type}
            onTypeChange={changeType}
            disaster={disaster}
            onChange={(key, v) => setDisaster((d) => ({ ...d, [key]: v }))}
          />
          <FactorPanel
            sliders={scenario.factor_sliders}
            values={factorValues}
            autoKeys={autoKeys}
            overrides={overrides}
            onChange={changeFactor}
            onReset={(key) => setOverrides((o) => o.filter((k) => k !== key))}
          />
          <CargoPanel
            def={scenario.cargo_slider}
            priority={cargo}
            onPriorityChange={setCargo}
            hubAvailable={hubAvailable}
            onHubChange={setHubAvailable}
          />
        </aside>

        <section className="order-1 h-[55vh] lg:order-2 lg:h-auto">
          <MapView scenario={scenario} network={network} result={result} />
        </section>

        <aside className="order-2 space-y-4 bg-slate-50 p-4 lg:order-3 lg:overflow-y-auto">
          <DecisionCard result={result} pending={pending} />
          <OptionsTable result={result} />
          <DriversChart result={result} />
          <ExplanationPanel result={result} granite={granite} onExplain={explain} />
        </aside>
      </main>

      <footer className="border-t border-slate-200 bg-white px-4 py-1.5 text-[11px] text-slate-500">
        Prototype trained on synthetic data. Recommendations support a human dispatcher and are not autonomous
        commands. Road data © OpenStreetMap contributors (ODbL).
      </footer>
    </div>
  );
}
