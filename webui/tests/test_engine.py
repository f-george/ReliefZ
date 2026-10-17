import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app import create_app  # noqa: E402
from engine import DISASTER_TYPES, Engine  # noqa: E402

ACTIONS = {"CONTINUE_MONITORING", "HOLD_POSITION", "REROUTE", "DIVERT_TO_BACKUP_HUB"}
LOCATIONS = ["valencia", "noto"]


@pytest.fixture(scope="session")
def eng():
    engine = Engine()
    assert sorted(engine.scenarios) == sorted(LOCATIONS), "missing a cached road graph in data/"
    return engine


def sim(eng, dtype="flood", hub=True, factors=None, overrides=None, location="valencia", **disaster):
    return eng.simulate({"location": location, "type": dtype, "disaster": disaster, "factors": factors or {},
                         "overrides": overrides or [], "backup_hub_available": hub})


@pytest.mark.parametrize("location", LOCATIONS)
def test_route_is_fixed(eng, location):
    first = eng.scenario(location)["route"]
    sim(eng, location=location, position_pct=30)
    assert Engine().scenario(location)["route"] == first


def test_locations_have_their_own_route_and_labels(eng):
    valencia, noto = eng.scenario("valencia"), eng.scenario("noto")
    assert valencia["route"] != noto["route"]
    assert noto["disaster_types"]["storm"]["short"] == "Typhoon"
    assert valencia["disaster_types"]["storm"]["short"] == "Storm"
    assert noto["names"]["hub"].startswith("Noto Airport")
    assert sim(eng, "storm", location="noto", position_pct=30)["facts"]["disaster"] == "Typhoon"


@pytest.mark.parametrize("location", LOCATIONS)
@pytest.mark.parametrize("dtype", list(DISASTER_TYPES))
@pytest.mark.parametrize("position", [0, 25, 50, 75, 100])
def test_outputs_are_valid(eng, location, dtype, position):
    r = sim(eng, dtype, location=location, position_pct=position)
    assert 0.0 <= r["risk_score"] <= 1.0
    assert r["action"] in ACTIONS
    assert r["gate_crossed"] == (r["risk_score"] >= r["threshold"])
    if not r["gate_crossed"]:
        assert r["action"] == "CONTINUE_MONITORING" and r["probabilities"] is None


def test_weak_disaster_means_continue(eng):
    for dtype in DISASTER_TYPES:
        assert sim(eng, dtype, position_pct=40, severity=0.05)["action"] == "CONTINUE_MONITORING"


def test_closer_flood_is_riskier(eng):
    assert sim(eng, position_pct=20)["risk_score"] > sim(eng, position_pct=90)["risk_score"]


def test_default_flood_reroutes_around_hazard(eng):
    r = sim(eng, position_pct=40)
    assert r["action"] == "REROUTE"
    reroute = next(o for o in r["options"] if o["action"] == "REROUTE")
    assert reroute["risk"] < r["risk_score"]
    assert r["routes"]["alternative"] is not None


@pytest.mark.parametrize("dtype,hub,disaster,expected", [
    ("flood", True, {"position_pct": 90}, "CONTINUE_MONITORING"),
    ("landslide", True, {"position_pct": 2}, "HOLD_POSITION"),
    ("storm", True, {"position_pct": 40}, "REROUTE"),
    ("storm", True, {"position_pct": 30, "duration_min": 240}, "DIVERT_TO_BACKUP_HUB"),
])
def test_every_action_is_reachable(eng, dtype, hub, disaster, expected):
    assert sim(eng, dtype, hub, **disaster)["action"] == expected


@pytest.mark.parametrize("dtype,hub,disaster,expected", [
    ("flood", True, {"position_pct": 80}, "CONTINUE_MONITORING"),
    ("flood", False, {"position_pct": 2}, "HOLD_POSITION"),
    ("flood", True, {"position_pct": 30}, "REROUTE"),
    ("flood", True, {"position_pct": 10}, "DIVERT_TO_BACKUP_HUB"),
])
def test_every_action_is_reachable_in_noto(eng, dtype, hub, disaster, expected):
    assert sim(eng, dtype, hub, location="noto", **disaster)["action"] == expected


@pytest.mark.parametrize("position", range(15, 75, 5))
def test_table_and_explanation_agree(eng, position):
    r = sim(eng, position_pct=position)
    assert f"{r['risk_score']:.2f}" in r["explanation"]
    assert r["gate_crossed"] == (r["risk_score"] >= r["threshold"])
    if r["action"] == "REROUTE":
        reroute = next(o for o in r["options"] if o["action"] == "REROUTE")
        assert f"{reroute['risk']:.2f}" in r["explanation"]


def test_disabling_hub_removes_divert(eng):
    r = sim(eng, "storm", hub=False, position_pct=30, duration_min=240)
    assert r["action"] != "DIVERT_TO_BACKUP_HUB"
    assert r["routes"]["hub"] is None


def test_override_replaces_auto_factor(eng):
    auto = sim(eng, position_pct=40)
    pinned = sim(eng, position_pct=40, factors={"distance_to_hazard_km": 25.0}, overrides=["distance_to_hazard_km"])
    assert pinned["model1_inputs"]["distance_to_hazard_km"] == 25.0
    assert pinned["auto_factors"]["distance_to_hazard_km"] == auto["auto_factors"]["distance_to_hazard_km"]
    assert pinned["risk_score"] < auto["risk_score"]


def test_inputs_are_clamped_and_validated(eng):
    r = sim(eng, position_pct=500, severity=-3)
    assert r["hazard"]["severity"] == 0.0
    with pytest.raises(ValueError):
        sim(eng, "earthquake")
    with pytest.raises(ValueError):
        sim(eng, position_pct="far")
    with pytest.raises(ValueError):
        sim(eng, location="atlantis")


def test_api(eng):
    client = create_app(eng).test_client()
    assert client.get("/api/scenario").get_json()["location"] == "valencia"
    for location in LOCATIONS:
        scenario = client.get(f"/api/scenario?location={location}").get_json()
        assert scenario["location"] == location and scenario["route_km"] > 0
        lines = client.get(f"/api/network?location={location}").get_json()["lines"]
        # every road segment is drawn exactly once
        assert sum(len(line) - 1 for line in lines) == eng.scenarios[location].G.number_of_edges()
    assert client.get("/api/scenario?location=atlantis").status_code == 400
    assert client.get("/api/network?location=atlantis").status_code == 400
    r = client.post("/api/simulate", json={"location": "noto", "type": "storm", "disaster": {"position_pct": 30}})
    assert r.status_code == 200 and r.get_json()["hazard"]["label"] == "Typhoon"
    r = client.post("/api/simulate", json={"type": "flood", "disaster": {"position_pct": 40}})
    body = r.get_json()
    assert r.status_code == 200
    assert {"risk_score", "action", "options", "routes", "hazard", "explanation", "facts"} <= body.keys()
    assert client.post("/api/simulate", json={"type": "volcano"}).status_code == 400
    assert client.post("/api/simulate", data="not json").status_code == 400


@pytest.mark.parametrize("body", [
    {"location": []}, {"location": {}}, {"type": []}, {"type": {}},
    {"disaster": []}, {"factors": []}, {"overrides": {}},
    {"backup_hub_available": "false"}, {"backup_hub_available": 0},
    {"disaster": {"severity": "Infinity"}}, {"disaster": {"severity": "NaN"}},
])
def test_api_rejects_malformed_simulation_inputs(eng, body):
    response = create_app(eng).test_client().post("/api/simulate", json=body)
    assert response.status_code == 400
    assert "error" in response.get_json()


@pytest.mark.parametrize("body", [[1], "explain", 123, {}, {"facts": []}])
def test_api_rejects_malformed_explanation_inputs(eng, body):
    response = create_app(eng).test_client().post("/api/explain", json=body)
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_platform_evidence_matches_server(eng):
    import platform

    response = create_app(eng).test_client().get("/api/scenario").get_json()
    assert response["platform"] == {"machine": platform.machine(), "python": platform.python_version()}


def test_missing_models_explain_setup(tmp_path, monkeypatch):
    monkeypatch.setattr("engine.ART", tmp_path)
    with pytest.raises(FileNotFoundError, match="scripts/prepare_demo.py"):
        Engine()
