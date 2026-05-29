from flask import Flask, request, jsonify
import numpy as np
from database import save_event
from model import train_models, get_scores
from utils import normalize_score, calculate_weighted_score, get_risk_label
from decision import get_action

app = Flask(__name__)

X_train = np.random.normal(0, 1, (100, 4))
models = train_models(X_train)


@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "message": "Anomaly Detection Flask API Running"
    })


@app.route("/analyze-event", methods=["POST"])
def analyze_event():
    if not request.is_json:
        return jsonify({
            "error": "Request must be JSON"
        }), 400

    data = request.get_json()

    required_fields = [
        "file_count",
        "operation_frequency",
        "unusual_time_access",
        "change_size"
    ]

    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        return jsonify({
            "error": "Missing required fields",
            "missing_fields": missing_fields
        }), 400

    test_event = np.array([[
        data["file_count"],
        data["operation_frequency"],
        data["unusual_time_access"],
        data["change_size"]
    ]])

    raw_scores = get_scores(models, test_event)

    normalized_scores = {
    "IF": normalize_score(raw_scores["IF"], 0, 1, invert=False),
    "LOF": normalize_score(raw_scores["LOF"], 0, 100, invert=False),
    "OCSVM": normalize_score(raw_scores["OCSVM"], 0, 15, invert=False),
    "EE": normalize_score(raw_scores["EE"], 0, 50000, invert=False)
}

    final_score = calculate_weighted_score(normalized_scores)
    risk_label = get_risk_label(final_score)
    action = get_action(final_score)

    response = {
        "input_event": {
            "file_count": data["file_count"],
            "operation_frequency": data["operation_frequency"],
            "unusual_time_access": data["unusual_time_access"],
            "change_size": data["change_size"]
        },
        "raw_scores": raw_scores,
        "normalized_scores": normalized_scores,
        "final_score": final_score,
        "risk_level": risk_label,
        "recommended_action": action
    }
    save_event(response)
    return jsonify(response)


if __name__ == "__main__":
    app.run(debug=True)