# ReliefSync Z — disaster simulator web UI

An interactive front end for the ReliefSync Z models. Pick a location and a disaster (**flood**, **severe storm**
(shown as **typhoon** in Japan) or **landslide**), place it anywhere along that location's fixed convoy route, and
adjust every risk factor with sliders. The page shows, live:
- the route risk (Model 1);
- the recommended action (Model 2): **CONTINUE**, **HALT**, **REROUTE** or **DIVERT TO HUB**;
- the route options compared;
- what drives the risk;
- an explanation, with an optional one from IBM Granite running locally.

All data is simulated. Road networks are cached OpenStreetMap extracts in `data/`.

## Locations

| Location | Route | Backup hub | Why it's here |
|---|---|---|---|
| Valencia, Spain | Depot → destination, 15.3 km (city roads) | Map corner | The October 2024 DANA floods |
| Noto Peninsula, Japan | Anamizu (relief staging) → Wajima, 23.3 km (rural, few detours) | Noto Airport, a relief base in 2024 | The 2024 Noto earthquake and the September 2024 floods and landslides that cut roads to Wajima |

Each location is defined in `locations.py`. Valencia's graph comes from notebook 04
(`data/road_graph.json`); Noto's was downloaded with `python webui/locations.py noto`
(`data/road_graph_noto.json`).

To add a location:
1. Add an entry to `LOCATIONS` with a bounding box and the origin, destination and hub coordinates.
2. Run `python webui/locations.py <key>` once, and commit the new `data/road_graph_<key>.json`.

Nothing else changes, because the models are not tied to a place.

## How it works

| Part | Technology | Location |
|---|---|---|
| Simulation engine | Python: scikit-learn, NetworkX, NumPy; llama.cpp for Granite | `engine.py` |
| Locations + road network downloader | Python, Overpass API (OpenStreetMap) | `locations.py` |
| API + static file server | Flask | `app.py` |
| User interface | React + Tailwind CSS (built with Vite), Leaflet map | `frontend/` (built files in `frontend/dist/`) |

The engine loads the trained models and road graph from the notebooks (`artifacts/`, `data/`), so
**run notebooks 01–04 first**. It reuses the routing and decision logic from notebooks 04 and 05.

Which risk factors are calculated automatically:
- **Distance to hazard:** how far the convoy travels along its route before reaching the disaster zone.
- **Road closure:** whether the route crosses an impassable section.
- **Flood risk:** for floods only, how badly the route is flooded.

These sliders show an **AUTO** tag. Drag one to set it yourself, and click **manual · reset** to go back.

## Run locally

From the repo root:

```bash
.venv/bin/pip install -r webui/requirements.txt
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

LinuxONE only needs Python and Flask; the React/Tailwind build happens on your laptop. Inside the LinuxONE Jupyter
container (open a terminal from Jupyter Lab):

```bash
cd ~/shared/ReliefZ
pip install -r webui/requirements.txt
python webui/app.py                     # listens on 127.0.0.1:8050 only
```

The app has no login, so it only listens locally by default. Reach it from your laptop through an SSH tunnel to the
LinuxONE VM:

```bash
ssh -L 8050:localhost:8050 linux1@<instance-public-IP>
# then open http://localhost:8050 on your laptop
```

The header shows **Running on s390x** when it is served from LinuxONE, which is useful evidence for the demo video.
The container runs with `--network host`, so the tunnel reaches the app directly.

The **Explain with Granite** button uses the same model search as notebook 05: `GRANITE_GGUF_PATH`, then `models/`,
then the container's preinstalled Granite model. On IBM Z the model file must be big-endian.

## Tests

```bash
.venv/bin/pytest webui/tests
```

The tests check, for both locations:
- each location keeps its own fixed route and labels (e.g. Typhoon in Japan);
- outputs stay in valid ranges;
- weak disasters lead to CONTINUE;
- a closer flood is riskier;
- each of the four actions can be reached;
- manual overrides work;
- inputs are validated;
- the table and explanation always show the same numbers;
- the API endpoints respond correctly.
