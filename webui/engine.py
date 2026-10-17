"""ReliefSync Z simulation engine for the web UI.

Ports the routing layer (notebooks/04_routing.ipynb) and the decision pipeline (notebooks/05_live_pipeline_demo.ipynb)
into an importable module. It loads the files the notebooks produce, so run notebooks 01-04 first.

The scenario is fixed: one convoy at the start of one simulated route through the cached OpenStreetMap road graph.
The user places a disaster somewhere along that route and adjusts the risk factors; the engine returns the
route risk (Model 1), the recommended action (Model 2) and the route options.
"""
import importlib.util
import json
import math
import os
import platform
import sys
import threading
import time
from pathlib import Path

import joblib
import networkx as nx
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
ART = ROOT / "artifacts"
DATA = ROOT / "data"

# Same values as notebook 04
BLOCK_THRESHOLD = 0.6     # edge hazard at/above this is impassable
HAZARD_PENALTY = 20.0     # safest route: cost = travel_min * (1 + HAZARD_PENALTY * hazard)
MAX_HAZARD_DISTANCE_KM = 50.0
# Web UI additions
ZONE_THRESHOLD = 0.1      # edge hazard at which a route counts as entering the hazard zone
REGIONAL_FLOOD_BASELINE = 0.10

DISASTER_TYPES = {
    "flood": {
        "label": "Flood",
        "short": "Flood",
        "model_type": "FLOOD",
        "color": "#2563eb",
        "auto_factors": ["flood_risk", "distance_to_hazard_km", "road_closure_nearby"],
        "disaster": {"radius_km": 1.0, "severity": 0.9, "duration_min": 240},
        "factors": {"rainfall_mm_per_hr": 40, "wind_speed_kmh": 30, "traffic_congestion": 0.50,
                    "route_delay_minutes": 35, "flood_risk": REGIONAL_FLOOD_BASELINE},
    },
    "storm": {
        "label": "Severe storm",
        "short": "Storm",
        "model_type": "SEVERE_WEATHER",
        "color": "#7c3aed",
        "auto_factors": ["distance_to_hazard_km", "road_closure_nearby"],
        "disaster": {"radius_km": 2.5, "severity": 0.8, "duration_min": 180},
        "factors": {"rainfall_mm_per_hr": 35, "wind_speed_kmh": 90, "traffic_congestion": 0.40,
                    "route_delay_minutes": 25, "flood_risk": 0.15},
    },
    "landslide": {
        "label": "Landslide",
        "short": "Landslide",
        "model_type": "ROAD_CLOSURE",
        "color": "#92400e",
        "auto_factors": ["distance_to_hazard_km", "road_closure_nearby"],
        "disaster": {"radius_km": 0.4, "severity": 1.0, "duration_min": 480},
        "factors": {"rainfall_mm_per_hr": 45, "wind_speed_kmh": 15, "traffic_congestion": 0.55,
                    "route_delay_minutes": 60, "flood_risk": 0.05},
    },
}

# Slider definitions; the frontend renders whatever is listed here.
DISASTER_SLIDERS = [
    {"key": "position_pct", "label": "Position along route", "min": 0, "max": 100, "step": 1, "unit": "%",
     "default": 40},
    {"key": "radius_km", "label": "Affected radius", "min": 0.2, "max": 3.0, "step": 0.1, "unit": "km",
     "default": 1.0},
    {"key": "severity", "label": "Severity", "min": 0.0, "max": 1.0, "step": 0.05, "unit": "", "default": 0.9},
    {"key": "duration_min", "label": "Expected duration", "min": 15, "max": 720, "step": 15, "unit": "min",
     "default": 240},
]
FACTOR_SLIDERS = [
    {"key": "speed_kmh", "label": "Vehicle speed", "min": 0, "max": 110, "step": 1, "unit": "km/h",
     "default": 55, "group": "Vehicle"},
    {"key": "fuel_level_pct", "label": "Fuel level", "min": 5, "max": 100, "step": 1, "unit": "%",
     "default": 68, "group": "Vehicle"},
    {"key": "rainfall_mm_per_hr", "label": "Rainfall", "min": 0, "max": 80, "step": 1, "unit": "mm/h",
     "default": 30, "group": "Weather"},
    {"key": "wind_speed_kmh", "label": "Wind speed", "min": 0, "max": 150, "step": 1, "unit": "km/h",
     "default": 30, "group": "Weather"},
    {"key": "flood_risk", "label": "Flood risk", "min": 0.0, "max": 1.0, "step": 0.01, "unit": "",
     "default": REGIONAL_FLOOD_BASELINE, "group": "Weather"},
    {"key": "traffic_congestion", "label": "Traffic congestion", "min": 0.0, "max": 1.0, "step": 0.01, "unit": "",
     "default": 0.45, "group": "Route"},
    {"key": "route_delay_minutes", "label": "Route delay", "min": 0, "max": 180, "step": 1, "unit": "min",
     "default": 35, "group": "Route"},
    {"key": "distance_to_hazard_km", "label": "Distance to hazard", "min": 0.0, "max": 30.0, "step": 0.1,
     "unit": "km", "default": 10.0, "group": "Route"},
    {"key": "road_closure_nearby", "label": "Road closure on route", "min": 0, "max": 1, "step": 1, "unit": "",
     "default": 0, "group": "Route"},
]
CARGO_SLIDER = {"key": "cargo_priority", "label": "Cargo priority", "min": 1, "max": 5, "step": 1, "unit": "",
                "default": 5}

ACTION_LABELS = {
    "CONTINUE_MONITORING": "Continue",
    "HOLD_POSITION": "Halt",
    "REROUTE": "Reroute",
    "DIVERT_TO_BACKUP_HUB": "Divert to hub",
}
FEATURE_LABELS = {
    "speed_kmh": "vehicle speed", "fuel_level_pct": "fuel level", "rainfall_mm_per_hr": "rainfall",
    "wind_speed_kmh": "wind", "flood_risk": "flood risk", "traffic_congestion": "congestion",
    "distance_to_hazard_km": "proximity to the hazard", "route_delay_minutes": "route delay",
    "road_closure_nearby": "a road closure on the route",
}
SYSTEM_PROMPT = (
    "You explain recommendations from a humanitarian logistics decision-support system to a human dispatcher. "
    "Write 2-3 plain sentences. Use ONLY the facts provided. Never recommend a different action, invent routes, "
    "or add numbers that are not in the facts."
)


class GraniteUnavailable(Exception):
    pass


# --------------------------------------------------------------------------- graph helpers (from notebook 04)
def haversine_km(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(np.radians, (lat1, lon1, lat2, lon2))
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return 6371.0 * 2 * np.arcsin(np.sqrt(a))


def add_road(G, u, v, speed_kmh, highway=""):
    length = float(haversine_km(G.nodes[u]["lat"], G.nodes[u]["lon"], G.nodes[v]["lat"], G.nodes[v]["lon"]))
    G.add_edge(u, v, length_km=length, speed_kmh=speed_kmh, travel_min=60 * length / speed_kmh, highway=highway)


def load_graph(path):
    payload = json.loads(path.read_text())
    G = nx.Graph(source=payload["source"])
    for n, lat, lon in payload["nodes"]:
        G.add_node(n, lat=lat, lon=lon)
    for u, v, speed, highway in payload["edges"]:
        add_road(G, u, v, speed, highway)
    return G


def pick_endpoints(G):
    """Depot/destination/backup hub: three opposite corners of the map (same as notebook 04)."""
    nodes = list(G.nodes)
    lat = np.array([G.nodes[n]["lat"] for n in nodes])
    lon = np.array([G.nodes[n]["lon"] for n in nodes])
    return nodes[int(np.argmin(lat + lon))], nodes[int(np.argmax(lat + lon))], nodes[int(np.argmax(lat - lon))]


def _clamp(value, slider):
    try:
        value = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{slider['key']} must be a number")
    if math.isnan(value):
        raise ValueError(f"{slider['key']} must be a number")
    return min(max(value, slider["min"]), slider["max"])


# --------------------------------------------------------------------------- Granite helpers (from notebook 05)
def _glob_granite(base, max_depth=4):
    for depth in range(max_depth + 1):
        yield from sorted(base.glob("*/" * depth + "*[Gg]ranite*.gguf"))


def find_granite_model():
    env_path = os.getenv("GRANITE_GGUF_PATH")
    if env_path:
        return Path(env_path) if Path(env_path).is_file() else None
    search = [ROOT / "models"]
    spec_ = importlib.util.find_spec("loan_demo")    # IBM's sample package in the LinuxONE container
    if spec_ and spec_.origin:
        search.append(Path(spec_.origin).parent)
    search += [Path("/home/ibm-user"), Path.home(), Path("/opt")]
    for base in search:
        if base.is_dir():
            match = next(_glob_granite(base), None)
            if match:
                return match
    return None


def gguf_byte_order(path):
    with open(path, "rb") as f:
        magic, version = f.read(4), f.read(4)
    if magic != b"GGUF":
        return "not a GGUF file"
    return "little" if int.from_bytes(version, "little") < 65536 else "big"


# --------------------------------------------------------------------------- engine
class Engine:
    def __init__(self):
        self.spec = json.loads((ART / "feature_spec.json").read_text())
        self.m1_features = self.spec["model1_features"]
        self.m2_features = self.spec["model2_categorical"] + self.spec["model2_numeric"]
        self.threshold = self.spec["risk_threshold"]
        self.calm = self.spec["calm_reference"]
        self.model1 = joblib.load(ART / "model1_rf.joblib")
        self.model2 = joblib.load(ART / "model2_rf.joblib")
        self.model1.set_params(n_jobs=1)
        self.model2.set_params(rf__n_jobs=1)

        G = self.G = load_graph(DATA / "road_graph.json")
        edges = list(G.edges)
        for eid, (u, v) in enumerate(edges):
            G[u][v]["eid"] = eid
        self.edge_mid_lat = np.array([(G.nodes[u]["lat"] + G.nodes[v]["lat"]) / 2 for u, v in edges])
        self.edge_mid_lon = np.array([(G.nodes[u]["lon"] + G.nodes[v]["lon"]) / 2 for u, v in edges])

        self.origin, self.destination, self.hub = pick_endpoints(G)
        self.baseline = nx.shortest_path(G, self.origin, self.destination, weight="travel_min")
        seg = [G[u][v]["length_km"] for u, v in zip(self.baseline[:-1], self.baseline[1:])]
        self.baseline_cum_km = np.concatenate([[0.0], np.cumsum(seg)])
        self.route_km = float(self.baseline_cum_km[-1])

        self.network_json = json.dumps({"segments": [
            [round(G.nodes[u]["lat"], 5), round(G.nodes[u]["lon"], 5),
             round(G.nodes[v]["lat"], 5), round(G.nodes[v]["lon"], 5)] for u, v in edges]})

        self._granite = None
        self._granite_path = None
        self._granite_error = None
        self._granite_lock = threading.Lock()

    # ----------------------------------------------------------------------- scenario description
    def coords(self, path):
        return [[round(self.G.nodes[n]["lat"], 5), round(self.G.nodes[n]["lon"], 5)] for n in path]

    def node_coords(self, n):
        return [self.G.nodes[n]["lat"], self.G.nodes[n]["lon"]]

    def scenario(self):
        defaults = DISASTER_TYPES["flood"]
        return {
            "route": self.coords(self.baseline),
            "route_km": round(self.route_km, 2),
            "origin": self.node_coords(self.origin),
            "destination": self.node_coords(self.destination),
            "hub": self.node_coords(self.hub),
            "threshold": self.threshold,
            "disaster_types": {k: {key: v[key] for key in ("label", "short", "color", "auto_factors", "disaster",
                                                          "factors")}
                               for k, v in DISASTER_TYPES.items()},
            "default_type": "flood",
            "disaster_sliders": [{**s, "default": defaults["disaster"].get(s["key"], s["default"])}
                                 for s in DISASTER_SLIDERS],
            "factor_sliders": [{**s, "default": defaults["factors"].get(s["key"], s["default"])}
                               for s in FACTOR_SLIDERS],
            "cargo_slider": CARGO_SLIDER,
            "actions": ACTION_LABELS,
            "source": self.G.graph.get("source", ""),
            "platform": {"machine": platform.machine(), "python": platform.python_version()},
        }

    # ----------------------------------------------------------------------- geometry
    def point_along(self, position_pct):
        target = position_pct / 100 * self.route_km
        i = int(np.clip(np.searchsorted(self.baseline_cum_km, target) - 1, 0, len(self.baseline) - 2))
        seg_len = self.baseline_cum_km[i + 1] - self.baseline_cum_km[i]
        t = 0.0 if seg_len == 0 else (target - self.baseline_cum_km[i]) / seg_len
        a, b = self.G.nodes[self.baseline[i]], self.G.nodes[self.baseline[i + 1]]
        return a["lat"] + t * (b["lat"] - a["lat"]), a["lon"] + t * (b["lon"] - a["lon"])

    def hazard_field(self, hazard):
        """Hazard intensity (0-1) for every edge, same formula as notebook 04's apply_hazards."""
        d = haversine_km(self.edge_mid_lat, self.edge_mid_lon, hazard["lat"], hazard["lon"])
        return hazard["severity"] * np.exp(-(d / hazard["radius_km"]) ** 2)

    def safest_route(self, source, target, field):
        def cost(u, v, d):
            h = field[d["eid"]]
            if h >= BLOCK_THRESHOLD:
                return None    # networkx skips edges whose weight is None
            return d["travel_min"] * (1 + HAZARD_PENALTY * h)
        try:
            return nx.shortest_path(self.G, source, target, weight=cost)
        except nx.NetworkXNoPath:
            return None

    def route_metrics(self, path, field, hazard):
        G = self.G
        edges = list(zip(path[:-1], path[1:]))
        exposures = np.array([field[G[u][v]["eid"]] for u, v in edges]) if edges else np.zeros(0)
        lengths = np.array([G[u][v]["length_km"] for u, v in edges]) if edges else np.zeros(0)
        cum = np.concatenate([[0.0], np.cumsum(lengths)])
        exposure = float(exposures.max()) if len(exposures) else 0.0

        # Approach distance: how far the convoy travels along this route before reaching the hazard.
        if hazard["severity"] < ZONE_THRESHOLD:
            distance = MAX_HAZARD_DISTANCE_KM            # too weak to have a hazard zone at all
        else:
            entering = np.flatnonzero(exposures >= ZONE_THRESHOLD)
            if len(entering):
                distance = float(cum[entering[0]])
            else:                                       # route passes by: travel to closest point + gap
                lats = np.array([G.nodes[n]["lat"] for n in path])
                lons = np.array([G.nodes[n]["lon"] for n in path])
                gap = haversine_km(lats, lons, hazard["lat"], hazard["lon"])
                k = int(np.argmin(gap))
                distance = float(cum[k] + gap[k])
        return {
            "travel_min": float(sum(G[u][v]["travel_min"] for u, v in edges)),
            "length_km": float(cum[-1]),
            "hazard_exposure": exposure,
            "blocked": exposure >= BLOCK_THRESHOLD,
            "distance_km": min(distance, MAX_HAZARD_DISTANCE_KM),
            "exposures": exposures,
        }

    # ----------------------------------------------------------------------- models
    def route_features(self, factors, dtype, metrics, delay_applies):
        f = {k: factors[k] for k in ("speed_kmh", "fuel_level_pct", "rainfall_mm_per_hr", "wind_speed_kmh",
                                     "traffic_congestion")}
        f["route_delay_minutes"] = factors["route_delay_minutes"] if delay_applies else 0.0
        f["flood_risk"] = (max(REGIONAL_FLOOD_BASELINE, metrics["hazard_exposure"]) if dtype == "flood"
                           else factors["flood_risk"])
        f["distance_to_hazard_km"] = round(metrics["distance_km"], 2)
        f["road_closure_nearby"] = int(metrics["blocked"])
        return f

    def predict_risk(self, features):
        # Rounded once to the 2 decimals shown in the UI, so the threshold check, the options table and the
        # explanation can never disagree (e.g. 0.749 displayed as 0.75 but not crossing the 0.75 gate).
        return round(float(np.clip(self.model1.predict(pd.DataFrame([features])[self.m1_features])[0], 0, 1)), 2)

    def risk_level(self, risk):
        return "HIGH" if risk >= self.threshold else "MEDIUM" if risk >= 0.4 else "LOW"

    def risk_drivers(self, features, top_k=4):
        """How much the risk drops when each feature alone is reset to its calm value (from notebook 05)."""
        rows = [features] + [{**features, f: self.calm[f]} for f in self.m1_features]
        preds = self.model1.predict(pd.DataFrame(rows)[self.m1_features])
        drops = sorted(((f, float(preds[0] - p)) for f, p in zip(self.m1_features, preds[1:])), key=lambda kv: -kv[1])
        return [{"feature": f, "label": FEATURE_LABELS[f], "risk_drop": round(d, 3)} for f, d in drops[:top_k] if d > 0.01]

    # ----------------------------------------------------------------------- request parsing
    def parse(self, body):
        if not isinstance(body, dict):
            raise ValueError("request body must be a JSON object")
        dtype = body.get("type", "flood")
        if dtype not in DISASTER_TYPES:
            raise ValueError(f"type must be one of {sorted(DISASTER_TYPES)}")
        preset = DISASTER_TYPES[dtype]
        disaster_in = body.get("disaster") or {}
        factors_in = body.get("factors") or {}
        if not isinstance(disaster_in, dict) or not isinstance(factors_in, dict):
            raise ValueError("disaster and factors must be JSON objects")
        disaster = {s["key"]: _clamp(disaster_in.get(s["key"], preset["disaster"].get(s["key"], s["default"])), s)
                    for s in DISASTER_SLIDERS}
        factors = {s["key"]: _clamp(factors_in.get(s["key"], preset["factors"].get(s["key"], s["default"])), s)
                   for s in FACTOR_SLIDERS}
        factors["road_closure_nearby"] = int(round(factors["road_closure_nearby"]))
        overrides = body.get("overrides") or []
        if not isinstance(overrides, list):
            raise ValueError("overrides must be a list")
        overrides = [k for k in overrides if k in preset["auto_factors"]]
        cargo = int(round(_clamp(body.get("cargo_priority", CARGO_SLIDER["default"]), CARGO_SLIDER)))
        hub_allowed = bool(body.get("backup_hub_available", True))
        return dtype, disaster, factors, overrides, cargo, hub_allowed

    # ----------------------------------------------------------------------- main entry point
    def simulate(self, body):
        t0 = time.perf_counter()
        dtype, disaster, factors, overrides, cargo, hub_allowed = self.parse(body)
        preset = DISASTER_TYPES[dtype]
        lat, lon = self.point_along(disaster["position_pct"])
        hazard = {"lat": lat, "lon": lon, "radius_km": disaster["radius_km"], "severity": disaster["severity"]}
        field = self.hazard_field(hazard)

        cur_m = self.route_metrics(self.baseline, field, hazard)
        auto = self.route_features(factors, dtype, cur_m, delay_applies=True)
        auto_factors = {k: auto[k] for k in preset["auto_factors"]}
        cur_f = {**auto, **{k: factors[k] for k in overrides}}
        risk = self.predict_risk(cur_f)

        exposed = [[self.coords([u])[0], self.coords([v])[0]]
                   for (u, v), e in zip(zip(self.baseline[:-1], self.baseline[1:]), cur_m["exposures"])
                   if e >= ZONE_THRESHOLD]
        result = {
            "type": dtype,
            "risk_score": round(risk, 3),
            "risk_level": self.risk_level(risk),
            "threshold": self.threshold,
            "gate_crossed": risk >= self.threshold,
            "action": "CONTINUE_MONITORING",
            "probabilities": None,
            "auto_factors": auto_factors,
            "model1_inputs": cur_f,
            "hazard": {**hazard, "color": preset["color"], "label": preset["label"]},
            "hazard_segments": exposed,
            "distance_ahead_km": round(cur_m["distance_km"], 2),
            "routes": {"alternative": None, "hub": None},
            "risk_drivers": self.risk_drivers(cur_f),
            "options": [{"action": "CONTINUE_MONITORING", "label": "Continue", "risk": round(risk, 3),
                         "minutes": 0.0, "minutes_label": "extra", "available": True, "note": "current route"}],
        }
        facts = {
            "disaster": preset["label"], "distance_ahead_km": result["distance_ahead_km"],
            "risk_score": round(risk, 2), "risk_level": result["risk_level"], "threshold": self.threshold,
            "risk_drivers": [d["label"] for d in result["risk_drivers"]],
            "estimated_hazard_duration_min": disaster["duration_min"], "cargo_priority": cargo,
        }

        if risk >= self.threshold:
            alt_path = self.safest_route(self.origin, self.destination, field)
            alt_ok = alt_path is not None and alt_path != self.baseline
            if alt_ok:
                alt_m = self.route_metrics(alt_path, field, hazard)
                alt_risk = self.predict_risk(self.route_features(
                    factors, dtype, alt_m, delay_applies=alt_m["hazard_exposure"] >= ZONE_THRESHOLD))
                detour = max(0.0, alt_m["travel_min"] - cur_m["travel_min"])
            else:
                alt_risk, detour = 1.0, 0.0
            hub_path = self.safest_route(self.origin, self.hub, field) if hub_allowed else None
            if hub_path:
                hub_m = self.route_metrics(hub_path, field, hazard)
                hub_risk = self.predict_risk(self.route_features(
                    factors, dtype, hub_m, delay_applies=hub_m["hazard_exposure"] >= ZONE_THRESHOLD))
            hold_risk = self.predict_risk({**self.calm, "fuel_level_pct": factors["fuel_level_pct"]})

            m2_row = {
                "disruption_type": preset["model_type"],
                "disruption_severity": disaster["severity"],
                "current_route_risk": risk,
                "alternative_route_available": int(alt_ok),
                "alternative_route_risk": alt_risk,
                "extra_detour_minutes": detour,
                "fuel_level_pct": factors["fuel_level_pct"],
                "cargo_priority": cargo,
                "estimated_hazard_duration_min": disaster["duration_min"],
                "backup_hub_available": int(hub_path is not None),
            }
            X2 = pd.DataFrame([m2_row])[self.m2_features]
            action = str(self.model2.predict(X2)[0])
            proba = {str(c): round(float(p), 3) for c, p in zip(self.model2.classes_, self.model2.predict_proba(X2)[0])}

            result.update(action=action, probabilities=proba)
            result["routes"] = {"alternative": self.coords(alt_path) if alt_ok else None,
                                "hub": self.coords(hub_path) if hub_path else None}
            result["options"] += [
                {"action": "HOLD_POSITION", "label": "Halt", "risk": round(hold_risk, 3),
                 "minutes": float(disaster["duration_min"]), "minutes_label": "extra", "available": True,
                 "note": "risk once the hazard clears"},
                {"action": "REROUTE", "label": "Reroute", "risk": round(alt_risk, 3) if alt_ok else None,
                 "minutes": round(detour, 1) if alt_ok else None, "minutes_label": "extra", "available": alt_ok,
                 "note": "safest alternative route" if alt_ok else "no route around the hazard"},
                {"action": "DIVERT_TO_BACKUP_HUB", "label": "Divert to hub",
                 "risk": round(hub_risk, 3) if hub_path else None,
                 "minutes": round(hub_m["travel_min"], 1) if hub_path else None, "minutes_label": "to hub",
                 "available": hub_path is not None,
                 "note": "backup hub" if hub_path else ("hub disabled" if not hub_allowed else "hub unreachable")},
            ]
            facts.update(alternative_route_available=alt_ok,
                         alternative_route_risk=round(alt_risk, 2) if alt_ok else None,
                         extra_detour_minutes=round(detour, 1) if alt_ok else None,
                         backup_hub_risk=round(hub_risk, 2) if hub_path else None)

        facts["recommended_action"] = result["action"]
        result["facts"] = facts
        result["explanation"] = template_explanation(facts, self.threshold)
        result["compute_ms"] = round(1000 * (time.perf_counter() - t0), 1)
        return result

    # ----------------------------------------------------------------------- Granite (llama.cpp, local)
    def _load_granite(self):
        if self._granite is not None or self._granite_error is not None:
            return
        path = find_granite_model()
        if path is None:
            self._granite_error = "no Granite GGUF model found (set GRANITE_GGUF_PATH or put one in models/)"
            return
        if gguf_byte_order(path) != sys.byteorder:
            self._granite_error = f"{path.name} does not match this machine's {sys.byteorder}-endian byte order"
            return
        try:
            from jinja2.sandbox import ImmutableSandboxedEnvironment
            from llama_cpp import Llama
            self._granite = Llama(model_path=str(path), n_ctx=2048, verbose=False)
            self._granite_template = ImmutableSandboxedEnvironment(trim_blocks=True, lstrip_blocks=True).from_string(
                self._granite.metadata["tokenizer.chat_template"])
            self._granite_path = path
        except Exception as exc:
            self._granite_error = f"could not load Granite: {exc}"

    def explain(self, facts):
        if not isinstance(facts, dict):
            raise ValueError("facts must be a JSON object")
        facts = {k: v for k, v in facts.items() if isinstance(k, str) and len(k) < 64}
        prompt_facts = json.dumps(facts)[:4000]
        with self._granite_lock:   # llama.cpp contexts are not thread-safe
            self._load_granite()
            if self._granite is None:
                raise GraniteUnavailable(self._granite_error)
            messages = [{"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": f"Facts: {prompt_facts}\nExplain the recommended action."}]
            prompt = self._granite_template.render(
                messages=messages, add_generation_prompt=True, enable_thinking=False, bos_token="", eos_token="",
                strftime_now=lambda fmt: time.strftime(fmt))
            t0 = time.perf_counter()
            out = self._granite.create_completion(prompt, temperature=0, max_tokens=160)
            seconds = time.perf_counter() - t0
        return {"text": out["choices"][0]["text"].split("</think>")[-1].strip(),
                "source": f"{self._granite_path.name} via llama.cpp (local)",
                "latency_s": round(seconds, 1)}


def template_explanation(facts, threshold):
    """Deterministic explanation; based on notebook 05's template, extended for the web UI's facts."""
    drivers = ", ".join(facts["risk_drivers"]) or "multiple factors"
    action = facts["recommended_action"]
    text = (f"{facts['disaster']} about {facts['distance_ahead_km']:.1f} km ahead. Route risk is "
            f"{facts['risk_score']:.2f} ({facts['risk_level']}), driven mainly by {drivers}. ")
    if action == "CONTINUE_MONITORING":
        text += (f"This is below the {threshold} intervention threshold, so the convoy continues and the "
                 "system keeps monitoring.")
    elif action == "REROUTE":
        extra = round(facts["extra_detour_minutes"])
        cost = f"+{extra} min of travel" if extra else "no extra travel time"
        text += (f"An alternative route lowers risk to {facts['alternative_route_risk']:.2f} for {cost}, "
                 "so rerouting is recommended.")
    elif action == "DIVERT_TO_BACKUP_HUB":
        hub = facts.get("backup_hub_risk")
        text += ("Diverting to the backup hub" + (f" (risk {hub:.2f})" if hub is not None else "") +
                 f" is recommended instead of waiting about {facts['estimated_hazard_duration_min']:.0f} minutes"
                 + ("." if facts.get("alternative_route_available") else " with no safe route to the destination."))
    elif action == "HOLD_POSITION":
        text += (f"The hazard is expected to last about {facts['estimated_hazard_duration_min']:.0f} minutes; "
                 "halting is safer than the available alternatives.")
    return text
