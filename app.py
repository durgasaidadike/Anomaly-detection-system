from flask import Flask, request, jsonify
import numpy as np
from database import save_event
from model import train_models, get_scores
from utils import normalize_score, calculate_weighted_score, get_risk_label
from decision import get_action
app = Flask(__name__)
X_train = np.random.normal(0, 1, (100, 4))
models = train_models(X_train)

@app.route("/analyze-event", methods=["POST"])
def analyze_event():
    try:

        if not request.is_json:
            return jsonify({
                "error": "Request must be JSON"
            }), 400

        data = request.get_json()

        event_type = data.get("event_type", "UNKNOWN")
        file_path = data.get("file_path", "UNKNOWN")

        required_fields = [
            "file_count",
            "operation_frequency",
            "unusual_time_access",
            "change_size"
        ]

        missing_fields = [
            field for field in required_fields
            if field not in data
        ]

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

        raw_scores = {
            key: float(value)
            for key, value in raw_scores.items()
        }

        normalized_scores = {
            "IF": float(
                normalize_score(
                    raw_scores["IF"],
                    0,
                    1,
                    invert=False
                )
            ),
            "LOF": float(
                normalize_score(
                    raw_scores["LOF"],
                    0,
                    100,
                    invert=False
                )
            ),
            "OCSVM": float(
                normalize_score(
                    raw_scores["OCSVM"],
                    0,
                    15,
                    invert=False
                )
            ),
            "EE": float(
                normalize_score(
                    raw_scores["EE"],
                    0,
                    50000,
                    invert=False
                )
            )
        }

        final_score = float(
            calculate_weighted_score(
                normalized_scores
            )
        )

        risk_label = str(
            get_risk_label(final_score)
        )

        action = str(
            get_action(final_score)
        )

        response = {
            "input_event": {
                "file_count": int(data["file_count"]),
                "operation_frequency": int(
                    data["operation_frequency"]
                ),
                "unusual_time_access": int(
                    data["unusual_time_access"]
                ),
                "change_size": float(
                    data["change_size"]
                ),
                "event_type": event_type,
                "file_path": file_path
            },
            "raw_scores": raw_scores,
            "normalized_scores": normalized_scores,
            "final_score": final_score,
            "risk_level": risk_label,
            "recommended_action": action
        }

        try:
            save_event(response)
        except Exception as mongo_error:
            print(
                "MongoDB Error:",
                str(mongo_error)
            )

        return jsonify(response)

    except Exception as e:

        print(
            "\n================ ERROR ================\n"
        )
        print(str(e))
        print(
            "\n=======================================\n"
        )

        return jsonify({
            "error": str(e)
        }), 500
if __name__ == "__main__":
     app.run(debug=True)
