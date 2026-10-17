# ReliefSync Z — disaster simulator web UI

An interactive front end for the ReliefSync Z models, served from IBM LinuxONE. Pick a location and a disaster
(**flood**, **severe storm** (shown as **typhoon** in Japan) or **landslide**), place it anywhere along that
location's fixed convoy route, and adjust every risk factor with sliders. The page shows, live:
- the route risk (Model 1);
- the recommended action (Model 2): **CONTINUE**, **HALT**, **REROUTE** or **DIVERT TO HUB**;
- the route options compared;
- what drives the risk;
- an explanation, with an optional one from IBM Granite running on the same machine.

For setup, starting the server, and connecting from your laptop, follow steps 4–5 of the
[usage guide in the main README](../README.md#usage-guide).

## Locations

| Location | Route | Backup hub | Why it's here |
|---|---|---|---|
| Valencia, Spain | Depot → destination, 15.3 km (city roads) | Map corner | The October 2024 DANA floods |
| Noto Peninsula, Japan | Anamizu (relief staging) → Wajima, 23.3 km (rural, few detours) | Noto Airport, a relief base in 2024 | The 2024 Noto earthquake and the September 2024 floods and landslides that cut roads to Wajima |

Both road networks are cached OpenStreetMap extracts in `data/` (`road_graph.json`, `road_graph_noto.json`), so the
web UI needs no internet access on LinuxONE. All other data is simulated.

## How it works

| Part | Technology | File |
|---|---|---|
| Simulation engine | Python: scikit-learn, NetworkX, NumPy; llama.cpp for Granite | `engine.py` |
| Location definitions | Python | `locations.py` |
| API + web server | Flask | `app.py` |
| Dashboard | React + Tailwind CSS + Leaflet map, prebuilt | `frontend/dist/` |

<<<<<<< HEAD
The engine loads the trained models and road graph from the notebooks (`artifacts/`, `data/`), so
**run `python scripts/prepare_demo.py` or notebooks 01–03 first**. The road graphs are already committed.
It adapts the routing and decision logic from notebooks 04 and 05; the web UI does not persist an audit log.
=======
The engine loads the models trained by notebooks 01–03 (`artifacts/`), so run those on LinuxONE first. It reuses
the routing and decision logic from notebooks 04 and 05.
>>>>>>> 1f77e04623295e5070081d46026ea2ca3247775f

Three risk factors are calculated from where you place the disaster:
- **Distance to hazard:** how far the convoy travels along its route before reaching the disaster zone.
- **Road closure:** whether the route crosses an impassable section.
- **Flood risk:** for floods only, how badly the route is flooded.

These sliders show an **AUTO** tag. Drag one to set it yourself, and click **manual · reset** to go back.

**Explain with Granite** uses the same model search as notebook 05: the `GRANITE_GGUF_PATH` environment variable,
then `models/`, then the Granite model preinstalled in the LinuxONE container. The model file must match the
machine's byte order, which is big-endian on IBM Z.

## Security

<<<<<<< HEAD
```bash
.venv/bin/pip install -r requirements-core.txt -r webui/requirements.txt
.venv/bin/python scripts/prepare_demo.py
.venv/bin/python webui/app.py           # → http://127.0.0.1:8050
```

The built frontend (`frontend/dist/`) is committed, so Node.js is **not** needed just to run the app.

To change the frontend, you need Node.js 20.19+ or 22.12+:

```bash
cd webui/frontend
npm ci
npm run dev        # live-reloading UI on http://localhost:5173 (keep app.py running for the API)
npm run build      # rebuild frontend/dist/ before committing
```

## Run on LinuxONE

LinuxONE only needs Python and Flask; the React/Tailwind build happens on your laptop. Before starting:
- **Notebooks 01–03 have run on LinuxONE**, so `artifacts/` holds models trained with the container's scikit-learn.
- **The repo is writable by the container user** (`chmod -R a+rwX` on the VM; see the main README). Notebook 00's
  *Project readiness* cell checks both.

Inside the LinuxONE Jupyter container (open a terminal from Jupyter Lab):

```bash
cd ~/shared/ReliefZ
pip install -r webui/requirements.txt  # Flask, pytest + 4 small dependencies, all pure Python (no compiling on s390x)
python -m pytest webui/tests            # optional: about 15 s
python webui/app.py                     # listens on 127.0.0.1:8050 only
```

If `pip install` reports a permission error, use `pip install --user -r webui/requirements.txt`. For an offline
container, download wheels on an internet-connected machine with a compatible Linux/s390x Python environment,
copy them over, then install with `pip install --no-index --find-links wheels -r webui/requirements.txt`.
Do not copy an unfiltered Windows wheel download: transitive dependencies such as MarkupSafe may be
platform-specific. Run this on the compatible environment:

```bash
pip download -d wheels -r webui/requirements.txt
```

The app has no login, so it only listens locally by default. Reach it from your laptop through an SSH tunnel to the
LinuxONE VM:

```bash
ssh -i <your key> -L 8050:localhost:8050 linux1@<instance-public-IP>
# then open http://localhost:8050 on your laptop
```

Shut down notebook 05's Jupyter kernel before clicking **Explain with Granite**, so the model isn't loaded into memory
twice on the VM.

The header shows **Running on s390x** when it is served from LinuxONE, which is useful evidence for the demo video.
The container runs with `--network host`, so the tunnel reaches the app directly.

The **Explain with Granite** button uses the same model search as notebook 05: `GRANITE_GGUF_PATH`, then `models/`,
then the container's preinstalled Granite model. On IBM Z the model file must be big-endian.
=======
- **Local only:** the server only listens on `127.0.0.1` (port 8050) and has no login. Reach it from your laptop
  through an encrypted SSH tunnel; don't open the port publicly.
- **No outside calls:** all inference, including Granite, runs on LinuxONE. The only external requests are the
  OpenStreetMap map tiles, which your browser loads directly.
>>>>>>> 1f77e04623295e5070081d46026ea2ca3247775f

## Tests

Inside the LinuxONE container, from the project folder:

```bash
python -m pytest webui/tests -q
```

The 60 tests check, for both locations:
- each location keeps its own fixed route and labels (e.g. Typhoon in Japan);
- outputs stay in valid ranges;
- weak disasters lead to CONTINUE;
- a closer flood is riskier;
- each of the four actions can be reached;
- manual overrides work;
- inputs are validated;
- the table and explanation always show the same numbers;
- the API endpoints respond correctly.
