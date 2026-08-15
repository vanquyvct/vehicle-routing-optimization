from __future__ import annotations

from pathlib import Path

from flask import Flask, jsonify, render_template, request

from optimizer import optimize_cvrp


BASE_DIR = Path(__file__).resolve().parent
app = Flask(__name__)


@app.get("/")
def index():
    sample_path = BASE_DIR / "data" / "sample.json"
    sample_text = sample_path.read_text(encoding="utf-8")
    return render_template("index.html", sample_json=sample_text)


@app.get("/api/health")
def health():
    return jsonify({"status": "ok", "service": "vehicle-routing-tttn"})


@app.post("/api/optimize")
def optimize():
    try:
        payload = request.get_json(force=True)
        result = optimize_cvrp(payload)
        return jsonify(result)
    except ValueError as exc:
        return jsonify({"status": "error", "message": str(exc)}), 400
    except Exception as exc:
        app.logger.exception("Unexpected error")
        return jsonify(
            {
                "status": "error",
                "message": f"Lỗi hệ thống: {type(exc).__name__}: {exc}",
            }
        ), 500


if __name__ == "__main__":
    app.run(debug=True)
