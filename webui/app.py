"""ReliefSync Z web UI server: JSON API + the built React frontend.

Run from the repo root:  .venv/bin/python webui/app.py            (http://127.0.0.1:8050)
"""
import argparse
from pathlib import Path

from flask import Flask, Response, jsonify, request, send_from_directory

from engine import Engine, GraniteUnavailable

DIST = Path(__file__).resolve().parent / "frontend" / "dist"


def create_app(engine=None):
    app = Flask(__name__, static_folder=None)
    app.json.sort_keys = False   # keep the engine's ordering (e.g. Flood, Storm, Landslide buttons)
    eng = engine or Engine()

    @app.get("/api/scenario")
    def scenario():
        return jsonify(eng.scenario())

    @app.get("/api/network")
    def network():
        return Response(eng.network_json, mimetype="application/json")

    @app.post("/api/simulate")
    def simulate():
        try:
            return jsonify(eng.simulate(request.get_json(silent=True)))
        except ValueError as exc:
            return jsonify(error=str(exc)), 400

    @app.post("/api/explain")
    def explain():
        body = request.get_json(silent=True) or {}
        try:
            return jsonify(eng.explain(body.get("facts")))
        except ValueError as exc:
            return jsonify(error=str(exc)), 400
        except GraniteUnavailable as exc:
            return jsonify(error=str(exc)), 503

    @app.get("/", defaults={"path": ""})
    @app.get("/<path:path>")
    def frontend(path):
        if not (DIST / "index.html").exists():
            return ("Frontend not built. Run: cd webui/frontend && npm ci && npm run build", 503)
        if path and (DIST / path).is_file():
            return send_from_directory(DIST, path)
        return send_from_directory(DIST, "index.html")

    return app


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ReliefSync Z disaster simulator web UI")
    parser.add_argument("--host", default="127.0.0.1",
                        help="interface to bind (default 127.0.0.1; use an SSH tunnel to reach it remotely)")
    parser.add_argument("--port", type=int, default=8050)
    args = parser.parse_args()
    create_app().run(host=args.host, port=args.port, threaded=True)
