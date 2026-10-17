"""Simulation locations for the web UI, plus a one-off downloader for their road networks.

Each location has a fixed convoy route. Road graphs are cached as JSON in data/ (same format as
notebooks/04_routing.ipynb), so the app never needs internet access at run time.

Download a location's road network once:  .venv/bin/python webui/locations.py noto
"""
import json
import sys
from pathlib import Path

import networkx as nx
import numpy as np
import requests

DATA = Path(__file__).resolve().parent.parent / "data"

LOCATIONS = {
    "valencia": {
        "label": "Valencia, Spain",
        "context": "Modelled on the October 2024 DANA floods south of Valencia.",
        "graph": DATA / "road_graph.json",          # created by notebook 04
        "endpoints": None,                          # use notebook 04's pick_endpoints (map corners)
        "names": {"origin": "Depot", "destination": "Destination", "hub": "Backup hub"},
        "type_labels": {},                          # default labels: Flood, Severe storm, Landslide
    },
    "noto": {
        "label": "Noto Peninsula, Japan",
        "context": ("Modelled on the 2024 Noto earthquake and the September 2024 heavy-rain floods and landslides, "
                    "which repeatedly cut relief roads to Wajima."),
        "graph": DATA / "road_graph_noto.json",
        "bbox": (37.20, 136.75, 37.42, 137.02),     # south, west, north, east
        "endpoints": {                              # (lat, lon), snapped to the nearest road node
            "origin": (37.2310, 136.9070),          # Anamizu: relief staging area
            "destination": (37.3905, 136.8990),     # Wajima city centre
            "hub": (37.2935, 136.9620),             # Noto Satoyama Airport: relief base in 2024
        },
        "names": {"origin": "Anamizu (staging)", "destination": "Wajima", "hub": "Noto Airport (relief base)"},
        "type_labels": {"storm": "Typhoon"},
    },
}

# Same road types and default speeds as notebook 04
DEFAULT_SPEED_KMH = {"motorway": 100, "trunk": 80, "primary": 60, "secondary": 50, "tertiary": 40,
                     "unclassified": 30}
OVERPASS_URLS = ["https://overpass-api.de/api/interpreter",
                 "https://overpass.kumi.systems/api/interpreter",
                 "https://maps.mail.ru/osm/tools/overpass/api/interpreter"]


def haversine_km(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(np.radians, (lat1, lon1, lat2, lon2))
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return 6371.0 * 2 * np.arcsin(np.sqrt(a))


def parse_speed(maxspeed, highway):
    try:
        return float(str(maxspeed).split()[0])
    except (TypeError, ValueError):
        return float(DEFAULT_SPEED_KMH.get(highway.replace("_link", ""), 30))


def fetch_osm_graph(bbox):
    """Download drivable roads in bbox from OpenStreetMap (port of notebook 04's fetch_osm_graph)."""
    s, w, n, e = bbox
    query = f"""
    [out:json][timeout:180];
    way["highway"~"^(motorway|trunk|primary|secondary|tertiary|unclassified)(_link)?$"]({s},{w},{n},{e});
    (._;>;);
    out body;
    """
    errors = []
    for url in OVERPASS_URLS:     # public servers are often busy; try mirrors in turn
        try:
            resp = requests.post(url, data={"data": query},
                                 headers={"User-Agent": "ReliefSyncZ-prototype/0.1"}, timeout=240)
            resp.raise_for_status()
            elements = resp.json()["elements"]
            break
        except Exception as exc:
            errors.append(f"{url}: {exc}")
    else:
        raise RuntimeError("; ".join(errors))

    G = nx.Graph(source=f"OpenStreetMap bbox={bbox}")
    for el in elements:
        if el["type"] == "node":
            G.add_node(el["id"], lat=el["lat"], lon=el["lon"])
    for el in elements:
        if el["type"] != "way":
            continue
        tags = el.get("tags", {})
        speed = parse_speed(tags.get("maxspeed"), tags.get("highway", ""))
        for u, v in zip(el["nodes"][:-1], el["nodes"][1:]):
            if u in G and v in G and u != v:
                G.add_edge(u, v, speed_kmh=speed, highway=tags.get("highway", ""))
    return G.subgraph(max(nx.connected_components(G), key=len)).copy()


def save_graph(G, path):
    """Same JSON layout as notebook 04's save_graph."""
    payload = {
        "source": G.graph.get("source", ""),
        "nodes": [[n, d["lat"], d["lon"]] for n, d in G.nodes(data=True)],
        "edges": [[u, v, d["speed_kmh"], d["highway"]] for u, v, d in G.edges(data=True)],
    }
    path.write_text(json.dumps(payload))


if __name__ == "__main__":
    key = sys.argv[1] if len(sys.argv) > 1 else "noto"
    loc = LOCATIONS[key]
    if "bbox" not in loc:
        sys.exit(f"{key} has no bbox; its graph comes from notebook 04")
    G = fetch_osm_graph(loc["bbox"])
    save_graph(G, loc["graph"])
    print(f"{loc['label']}: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges -> {loc['graph']}")
