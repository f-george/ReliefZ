# ReliefSync Z - disaster simulator web UI

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

The engine loads the models trained by notebooks 01–03 (`artifacts/`), so run those on LinuxONE first. It reuses
the routing and decision logic from notebooks 04 and 05.
=======
The engine loads the models trained by notebooks 01–03 (`artifacts/`), so run those on LinuxONE first. It reuses
the routing and decision logic from notebooks 04 and 05.

Three risk factors are calculated from where you place the disaster:
- **Distance to hazard:** how far the convoy travels along its route before reaching the disaster zone.
- **Road closure:** whether the route crosses an impassable section.
- **Flood risk:** for floods only, how badly the route is flooded.

These sliders show an **AUTO** tag. Drag one to set it yourself, and click **manual · reset** to go back.

**Explain with Granite** uses the same model search as notebook 05: the `GRANITE_GGUF_PATH` environment variable,
then `models/`, then the Granite model preinstalled in the LinuxONE container. The model file must match the
machine's byte order, which is big-endian on IBM Z.

## Security

- **Local only:** the server only listens on `127.0.0.1` (port 8050) and has no login. Reach it from your laptop
  through an encrypted SSH tunnel; don't open the port publicly.
- **No outside calls:** all inference, including Granite, runs on LinuxONE. The only external requests are the
  OpenStreetMap map tiles, which your browser loads directly.
  
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
