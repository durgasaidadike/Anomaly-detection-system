import numpy as np

from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor
from sklearn.svm import OneClassSVM
from sklearn.covariance import EllipticEnvelope

def train_models(X_train):

    models = {}

    models["IF"] = IsolationForest(contamination=0.1)
    models["IF"].fit(X_train)

    models["LOF"] = LocalOutlierFactor(
        contamination=0.1,
        novelty=True
    )
    models["LOF"].fit(X_train)

    models["OCSVM"] = OneClassSVM(gamma='auto')
    models["OCSVM"].fit(X_train)

    models["EE"] = EllipticEnvelope(contamination=0.1)
    models["EE"].fit(X_train)

    return models

def get_scores(models, test_event):

    isolation_score = abs(
        models["IF"].decision_function(test_event)[0]
    )

    lof_score = abs(
        models["LOF"].score_samples(test_event)[0]
    )

    ocsvm_score = abs(
        models["OCSVM"].decision_function(test_event)[0]
    )

    ee_score = abs(
        models["EE"].decision_function(test_event)[0]
    )

    return {
        "IF": isolation_score,
        "LOF": lof_score,
        "OCSVM": ocsvm_score,
        "EE": ee_score
    }