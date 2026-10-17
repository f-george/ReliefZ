# ReliefSync Z — relief convoy diversion

Hybrid-AI disaster logistics decision support for IBM Z Datathon 2026. The system takes live convoy telemetry,
estimates route risk (Model 1), recommends an action (Model 2), computes reroutes on an OpenStreetMap road graph,
and explains the decision in plain language (Granite). A human dispatcher always makes the final call.
See `ReliefSync_Z_Detailed_Project_Summary-3.docx` for the full design.

## Notebooks (run in order)

| Notebook | Purpose | Produces |
|---|---|---|
| `00_environment_check` | Architecture, byte order, library versions, IBM Z CPU features (deployment evidence) | — |
| `01_synthetic_data` | Shared feature spec + synthetic training data for both models | `artifacts/feature_spec.json`, `data/*.csv` |
| `02_model1_risk` | Random Forest regressor + XGBoost benchmark, metrics, inference latency | `artifacts/model1_*` |
| `03_model2_action` | Random Forest classifier for CONTINUE / HOLD / REROUTE / DIVERT | `artifacts/model2_rf.joblib` |
| `04_routing` | OSM road graph (Overpass → cached JSON), hazard model, fastest vs safest route | `data/road_graph.json` |
| `05_live_pipeline_demo` | End-to-end live scenario: flood injected → risk spikes → reroute → explanation → audit log | `logs/audit_log.jsonl` |

`05` loads `04` with `%run`, so the routing functions live in one place.

## Local setup

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/jupyter lab notebooks/
```

## Moving to LinuxONE (s390x)

1. Copy the repo **including `data/road_graph.json`**, so no internet access is needed for routing.
2. Install the dependencies. On s390x, pip may have to compile scikit-learn and xgboost from source, which needs
   gcc/g++, cmake and the Python headers. If that fails, use conda (Anaconda publishes `linux-s390x` packages)
   or IBM's Python AI Toolkit for IBM Z and LinuxONE.
3. Run `00` first and screenshot it: it should show `s390x` and `big` byte order.
4. **Re-run `01` → `05` on LinuxONE** instead of copying model binaries. Everything is seeded and trains in
   about a minute. joblib pickles are only safe to load with the same scikit-learn version, and retraining
   on LinuxONE is also stronger evidence of a live workload. (XGBoost models are saved as portable JSON.)

## Granite explanations

Set these before starting Jupyter. Without them, notebook `05` uses a deterministic template that is labelled as such.

```bash
export WATSONX_APIKEY=...
export WATSONX_PROJECT_ID=...
export WATSONX_URL=https://us-south.ml.cloud.ibm.com     # your region
export GRANITE_MODEL_ID=ibm/granite-3-8b-instruct         # check which Granite models your project offers
```

## Next steps

- Wrap `analyse()` from notebook `05` in a small FastAPI/Flask service and containerise it with Podman on LinuxONE.
- Build the dispatcher dashboard on top of that endpoint.
- Tune the synthetic risk formula in `01`. Currently the rerouted convoy settles at ~0.44 risk because the regional
  weather still contributes.

All training data is synthetic. Production use would require validation against real operational outcomes.
