import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app import create_app  # noqa: E402
from engine import DISASTER_TYPES, Engine  # noqa: E402

ACTIONS = {"CONTINUE_MONITORING", "HOLD_POSITION", "REROUTE", "DIVERT_TO_BACKUP_HUB"}


@pytest.fixture(scope="session")
def eng():
    return Engine()


def sim(eng, dtype="flood", hub=True, factors=None, overrides=None, **disaster):
    return eng.simulate({"type": dtype, "disaster": disaster, "factors": factors or {},
                         "overrides": overrides or [], "backup_hub_available": hub})


def test_route_is_fixed(eng):
    first = eng.scenario()["route"]
    sim(eng, position_pct=30)
    assert Engine().scenario()["route"] == first


@pytest.mark.parametrize("dtype", list(DISASTER_TYPES))
@pytest.mark.parametrize("position", [0, 25, 50, 75, 100])
def test_outputs_are_valid(eng, dtype, position):
    r = sim(eng, dtype, position_pct=position)
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


def test_api(eng):
    client = create_app(eng).test_client()
    assert client.get("/api/scenario").get_json()["route_km"] > 0
    assert len(client.get("/api/network").get_json()["segments"]) == eng.G.number_of_edges()
    r = client.post("/api/simulate", json={"type": "flood", "disaster": {"position_pct": 40}})
    body = r.get_json()
    assert r.status_code == 200
    assert {"risk_score", "action", "options", "routes", "hazard", "explanation", "facts"} <= body.keys()
    assert client.post("/api/simulate", json={"type": "volcano"}).status_code == 400
    assert client.post("/api/simulate", data="not json").status_code == 400
