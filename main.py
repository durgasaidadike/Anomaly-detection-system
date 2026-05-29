import numpy as np
from model import train_models, get_scores
from utils import normalize_score, calculate_weighted_score, get_risk_label
from decision import get_action
from events import unusual_access


X_train = np.random.normal(0, 1, (100, 4))

test_event = unusual_access()

models = train_models(X_train)
raw_scores = get_scores(models, test_event)

normalized_scores = {
    "IF": normalize_score(raw_scores["IF"], -1, 1, invert=True),
    "LOF": normalize_score(raw_scores["LOF"], -5, 5, invert=True),
    "OCSVM": normalize_score(raw_scores["OCSVM"], -2, 2, invert=True),
    "EE": normalize_score(raw_scores["EE"], -10, 10, invert=True)
}

final_score = calculate_weighted_score(normalized_scores)
risk_label = get_risk_label(final_score)
action = get_action(final_score)

print("\n========== ANOMALY DETECTION REPORT ==========\n")

print("TEST EVENT")
print(test_event)

print("\nRAW SCORES")
print(f"Isolation Forest Score : {raw_scores['IF']:.4f}")
print(f"LOF Score              : {raw_scores['LOF']:.4f}")
print(f"OCSVM Score            : {raw_scores['OCSVM']:.4f}")
print(f"Elliptic Envelope      : {raw_scores['EE']:.4f}")

print("\nNORMALIZED ANOMALY SCORES")
print(f"Isolation Forest Score : {normalized_scores['IF']:.4f}")
print(f"LOF Score              : {normalized_scores['LOF']:.4f}")
print(f"OCSVM Score            : {normalized_scores['OCSVM']:.4f}")
print(f"Elliptic Envelope      : {normalized_scores['EE']:.4f}")

print(f"\nFinal Weighted Score   : {final_score:.4f}")
print(f"Risk Level             : {risk_label}")
print(f"Recommended Action     : {action}")