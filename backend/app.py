"""
app.py
------
Flask REST API for the Chemical Reaction Kinetics Analyzer.

This backend only processes data sent directly in the request body
(typed values or an uploaded CSV file). It performs no file-system
scanning, no access to credentials/secrets, and no external network
or account actions.

Run locally:
    python app.py

Run in production (Render):
    gunicorn app:app
"""

import os

from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd

from services.validation import (
    validate_time_concentration,
    validate_csv_dataframe,
    ValidationError,
)
from services.integral_method import full_integral_analysis
from services.differential_method import run_differential_method, guess_and_test_differential
from services.autocatalytic import run_autocatalytic
from services.reversible import run_reversible
from services.irreversible import run_irreversible
from services.prediction import predict_concentration, predict_time, predict_rate

app = Flask(__name__)
# Allow the separately-deployed static frontend to call this API from any origin.
CORS(app)


@app.route("/", methods=["GET"])
def root():
    return jsonify({
        "service": "Chemical Reaction Kinetics Analyzer API",
        "status": "running",
        "endpoints": [
            "/api/health",
            "/api/parse-csv",
            "/api/analyze/integral",
            "/api/analyze/differential",
            "/api/analyze/irreversible",
            "/api/analyze/autocatalytic",
            "/api/analyze/reversible",
            "/api/predict",
        ],
    })


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/api/parse-csv", methods=["POST"])
def parse_csv():
    """Parse an uploaded CSV containing 'Time' and 'Concentration' columns."""
    try:
        if "file" not in request.files:
            return jsonify({"error": "No file was uploaded."}), 400

        file = request.files["file"]
        if file.filename == "":
            return jsonify({"error": "No file was selected."}), 400
        if not file.filename.lower().endswith(".csv"):
            return jsonify({"error": "Only .csv files are supported."}), 400

        df = pd.read_csv(file)
        df.columns = [str(c).strip() for c in df.columns]

        time_col, conc_col = validate_csv_dataframe(df)

        time_values = df[time_col].tolist()
        conc_values = df[conc_col].tolist()

        return jsonify({"time": time_values, "concentration": conc_values})

    except ValidationError as e:
        return jsonify({"error": str(e)}), 400
    except pd.errors.EmptyDataError:
        return jsonify({"error": "The uploaded CSV file is empty."}), 400
    except pd.errors.ParserError:
        return jsonify({"error": "The uploaded file could not be parsed as a valid CSV."}), 400
    except Exception as e:
        return jsonify({"error": f"Failed to parse CSV: {str(e)}"}), 400


@app.route("/api/analyze/integral", methods=["POST"])
def analyze_integral():
    try:
        data = request.get_json(force=True) or {}
        t, C = validate_time_concentration(data.get("time"), data.get("concentration"))
        result = full_integral_analysis(t, C)
        result["original_data"] = [{"time": ti, "concentration": ci} for ti, ci in zip(t, C)]
        return jsonify(result)
    except ValidationError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Analysis failed: {str(e)}"}), 400


@app.route("/api/analyze/differential", methods=["POST"])
def analyze_differential():
    try:
        data = request.get_json(force=True) or {}
        t, C = validate_time_concentration(data.get("time"), data.get("concentration"))
        result = run_differential_method(t, C)
        guess_results, guess_best = guess_and_test_differential(t, C)
        result["guess_and_test"] = guess_results
        result["guess_and_test_best"] = guess_best
        result["original_data"] = [{"time": ti, "concentration": ci} for ti, ci in zip(t, C)]
        return jsonify(result)
    except ValidationError as e:
        return jsonify({"error": str(e)}), 400
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Analysis failed: {str(e)}"}), 400


@app.route("/api/analyze/irreversible", methods=["POST"])
def analyze_irreversible():
    try:
        data = request.get_json(force=True) or {}
        t, C = validate_time_concentration(data.get("time"), data.get("concentration"))
        mode = data.get("mode", "integral")
        if mode not in ("integral", "differential"):
            mode = "integral"
        result = run_irreversible(t, C, mode=mode)
        result["original_data"] = [{"time": ti, "concentration": ci} for ti, ci in zip(t, C)]
        return jsonify(result)
    except ValidationError as e:
        return jsonify({"error": str(e)}), 400
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Analysis failed: {str(e)}"}), 400


@app.route("/api/analyze/autocatalytic", methods=["POST"])
def analyze_autocatalytic():
    try:
        data = request.get_json(force=True) or {}
        t = data.get("time")
        C_A = data.get("concentration_a")
        C_B = data.get("concentration_b")

        if not t or not C_A or not C_B:
            return jsonify({"error": "Time, Concentration A, and Concentration B are all required."}), 400

        result = run_autocatalytic(t, C_A, C_B)
        return jsonify(result)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Analysis failed: {str(e)}"}), 400


@app.route("/api/analyze/reversible", methods=["POST"])
def analyze_reversible():
    try:
        data = request.get_json(force=True) or {}
        t, C_A = validate_time_concentration(data.get("time"), data.get("concentration"))
        C_A0 = data.get("C_A0")
        C_Ae = data.get("C_Ae")
        result = run_reversible(t, C_A, C_A0=C_A0, C_Ae=C_Ae)
        return jsonify(result)
    except (ValidationError, ValueError) as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Analysis failed: {str(e)}"}), 400


@app.route("/api/predict", methods=["POST"])
def predict():
    try:
        data = request.get_json(force=True) or {}
        kind = data.get("type")
        n = float(data.get("n"))
        k = float(data.get("k"))
        C_A0 = float(data.get("C_A0"))

        if kind == "concentration":
            t = float(data.get("t"))
            value = predict_concentration(t, n, k, C_A0)
            return jsonify({"C_A": value})

        if kind == "time":
            C_A = float(data.get("C_A"))
            value = predict_time(C_A, n, k, C_A0)
            return jsonify({"t": value})

        if kind == "rate":
            C_A = float(data.get("C_A"))
            value = predict_rate(C_A, n, k)
            return jsonify({"rate": value})

        return jsonify({"error": "Invalid prediction type. Use 'concentration', 'time', or 'rate'."}), 400

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except (TypeError, KeyError):
        return jsonify({"error": "Missing or invalid input for prediction."}), 400
    except Exception as e:
        return jsonify({"error": f"Prediction failed: {str(e)}"}), 400


@app.errorhandler(404)
def not_found(_e):
    return jsonify({"error": "Endpoint not found."}), 404


@app.errorhandler(500)
def server_error(_e):
    return jsonify({"error": "An unexpected server error occurred."}), 500


if __name__ == "__main__":
    # Render provides the PORT environment variable; never hardcode a port.
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
