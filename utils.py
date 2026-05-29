def clamp(value, min_value=0.0, max_value=1.0):
    return max(min_value, min(value, max_value))


def normalize_score(score, min_val, max_val, invert=False):
    if max_val == min_val:
        return 0.0

    normalized = (score - min_val) / (max_val - min_val)
    normalized = clamp(normalized, 0.0, 1.0)

    if invert:
        normalized = 1.0 - normalized

    return round(normalized, 4)


def calculate_weighted_score(normalized_scores):
    weights = {
        "IF": 0.30,
        "LOF": 0.30,
        "OCSVM": 0.20,
        "EE": 0.20
    }

    final_score = sum(normalized_scores[model] * weights[model] for model in weights)
    return round(final_score, 4)


def get_risk_label(final_score):
    if final_score < 0.30:
        return "NORMAL"
    elif final_score < 0.60:
        return "MEDIUM"
    else:
        return "HIGH"