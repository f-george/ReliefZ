# ReliefSync Z_IBM Z Datathon 2026 Project

**Team:** ReliefSync Z · **Theme:** Real-time AI for critical decisions · **Event code:** SSF2026

Hybrid-AI disaster logistics decision support running on IBM LinuxONE. The system takes live convoy telemetry,
estimates route risk (Model 1), recommends an action (Model 2), computes reroutes on an OpenStreetMap road graph,
and explains the decision in plain language with IBM Granite running locally in llama.cpp. A human dispatcher always
makes the final call, and every decision goes into a tamper-evident audit log.
See `ReliefSync_Z_Detailed_Project_Summary-3.docx` for the full design.

Everything is open source, and no data leaves the machine during the demo. See [OPEN_SOURCE.md](OPEN_SOURCE.md) for
the libraries, model and data used, with links and licences.

## Notebooks (run in order)

| Notebook | Purpose | Produces |
|---|---|---|
| `00_environment_check` | Architecture, byte order, versions vs the LinuxONE container, container / zDNN / NNPA evidence | — |
| `01_synthetic_data` | Shared feature spec + synthetic training data for both models | `artifacts/feature_spec.json`, `data/*.csv` |
| `02_model1_risk` | Random Forest regressor (scikit-learn) + XGBoost benchmark, metrics, inference latency | `artifacts/model1_*` |
| `03_model2_action` | Random Forest classifier for CONTINUE / HOLD / REROUTE / DIVERT | `artifacts/model2_rf.joblib` |
| `04_routing` | OSM road graph (Overpass → cached JSON), hazard model, fastest vs safest route | `data/road_graph.json` |
| `05_live_pipeline_demo` | Live scenario: flood injected → risk spikes → reroute → Granite explanation → hash-chained audit log | `logs/audit_log.jsonl` |
| `06_scalability_benchmark` | Convoys scored per second at batch sizes 1–10,000, on one core vs all cores | `artifacts/benchmark.json` |

`05` loads `04` with `%run`, so the routing functions live in one place.

## Interactive web UI (`webui/`)

A browser-based disaster simulator for the demo video:
- choose a location: Valencia, Spain or the Noto Peninsula, Japan;
- choose a flood, severe storm (typhoon in Japan) or landslide;
- place it anywhere along the convoy's fixed route;
- adjust every risk factor with sliders.

It shows the live decision (CONTINUE / HALT / REROUTE / DIVERT TO HUB) on a map, compares the route options, and
can ask Granite to explain the decision. It uses Flask + React + Tailwind CSS, and needs notebooks 01–04 to have run.

```bash
.venv/bin/pip install -r webui/requirements.txt
.venv/bin/python webui/app.py      # → http://127.0.0.1:8050
```

See [webui/README.md](webui/README.md) for LinuxONE (SSH tunnel) and frontend development.

## Running on LinuxONE Community Cloud

Use the official Jupyter Lab ML container (https://github.com/linuxone-community-cloud/jupyter-lab-ml). It already
has scikit-learn, XGBoost, llama.cpp with the zDNN backend, and an IBM Granite model, so there is nothing to compile.

On the LinuxONE VM (`ssh -i <your key> linux1@<instance-public-IP>`):

```bash
docker pull registry.linuxone.cloud.marist.edu/l1cc/jupyterlab-image-s390x:latest
mkdir -p /home/linux1/shared && chmod a+w /home/linux1/shared
git clone <this repo> /home/linux1/shared/ReliefZ
# Jupyter runs as a different user inside the container, so it must be able to write into the repo
chmod -R a+rwX /home/linux1/shared/ReliefZ
docker run --network host --name notebook -v /home/linux1/shared:/home/ibm-user/shared \
  -d registry.linuxone.cloud.marist.edu/l1cc/jupyterlab-image-s390x:latest
sudo iptables -I INPUT -p tcp --dport 38888 -j ACCEPT
# open http://<instance-public-IP>:38888 and go to shared/ReliefZ/notebooks
```

Then, in Jupyter on LinuxONE:
1. **Run `00` and screenshot it.** It should show `s390x`, big-endian byte order, the container, and the zDNN library.
   Its last cell, *Project readiness*, should show no FAIL lines.
2. **Run `01` → `06` in order.** Retrain on LinuxONE rather than copying `.joblib` files: training takes about a
   minute, and it is stronger evidence of a live workload. The road networks are in the repo, so no internet is needed.
3. **In `05`, check the explanation source.** It should name a Granite `.gguf` file, not "template". Notebook 05 finds
   the container's preinstalled Granite model automatically (`loan_demo.rag_utils.MODEL_PATH`). If it still says
   "template", set `GRANITE_GGUF_PATH` to a big-endian GGUF: IBM Z is big-endian, and models downloaded from Hugging
   Face are little-endian (convert with llama.cpp's `gguf_convert_endian.py <file> big`).
4. **Start the web UI** from a Jupyter terminal; see [webui/README.md](webui/README.md). Shut down notebook 05's kernel
   first, so Granite isn't loaded into memory twice.
5. **Take screenshots for the video and the technical-design score:** `docker ps`, `top` or `htop` during notebook 06,
   the outputs of notebooks 05 and 06, and the web UI header showing "Running on s390x".

### What runs where

| Step | Where | Why |
|---|---|---|
| Notebooks 00–06: environment check, training, routing, live demo, benchmark | **LinuxONE** | The models must be trained with the container's scikit-learn, and this is the workload judges want to see |
| Web UI server (`webui/app.py`) and its tests | **LinuxONE** | Pure Python; only Flask needs installing |
| Viewing the web UI and Jupyter, recording the video | **Your laptop's browser** | Through the SSH tunnel / port 38888 |
| Building the web UI frontend (`npm run build`) | **Laptop only** | Tailwind CSS has no s390x build; the built `webui/frontend/dist/` is committed |
| Downloading road networks from OpenStreetMap | **Laptop** (already done) | One-off; the results in `data/` are committed |
| Downloading a Granite model from Hugging Face | **Laptop only** (for local testing) | LinuxONE uses the container's own big-endian Granite model |

## Running locally (x86 / ARM)

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt     # builds llama-cpp-python from source (needs cmake + a C++ compiler)
mkdir -p models && curl -L -o models/granite-4.2-3b-Q4_K_M.gguf \
  https://huggingface.co/ibm-granite/granite-4.2-3b-GGUF/resolve/main/granite-4.2-3b-Q4_K_M.gguf
.venv/bin/jupyter lab notebooks/
```

Without a Granite model, notebook 05 still runs and uses a template explanation, which is labelled as such.

## Submission checklist (from the participant guidebook)

- [ ] Project title in the format `ReliefSync Z_IBM Z Datathon 2026 Project`
- [ ] Event code `SSF2026` in the project description
- [ ] Demo video of **3 minutes or less**: problem, supporting data, solution, how it uses IBM Z (tech stack, the
      LinuxONE instance and the model running)
- [ ] GitHub repo link
- [ ] Links to the open-source resources used ([OPEN_SOURCE.md](OPEN_SOURCE.md))
- [ ] Both mandatory AI/ML labs completed (Predictive AI hybrid multi-model; Predictive AI + Generative AI)
- [ ] Optional: architecture flowchart (Figure 1 in the project summary), prototype

All training data is synthetic. Production use would require validation against real operational outcomes.
