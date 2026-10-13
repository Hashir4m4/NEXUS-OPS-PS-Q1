"""
Classical Machine Learning Models Module
========================================
NEXUS-OPS | PS-Q1: Biomedical Signal Classifier (Milestone 4)

Provides standardized, frozen classical candidate models for binary ECG beat
classification (Normal Sinus 'N'=0 vs Ventricular Ectopic Beat 'V'=1):
1. Logistic Regression (L2 regularized linear baseline with coefficient interpretability).
2. Support Vector Machine with RBF kernel (non-linear maximum-margin boundary).
3. Random Forest (non-linear decision tree ensemble with Gini feature importances).

Hyperparameters and seeds are strictly frozen and documented prior to evaluation.
"""

from typing import Dict, Any
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.ensemble import RandomForestClassifier

DEFAULT_RANDOM_STATE = 42

MODEL_CONFIGS: Dict[str, Dict[str, Any]] = {
    "logistic_regression": {
        "model_class": "LogisticRegression",
        "description": "L2-regularized logistic regression (linear baseline)",
        "params": {
            "C": 1.0,
            "penalty": "l2",
            "solver": "lbfgs",
            "max_iter": 1000,
            "random_state": DEFAULT_RANDOM_STATE,
        },
    },
    "svm_rbf": {
        "model_class": "SVC",
        "description": "Support Vector Classifier with Radial Basis Function kernel",
        "params": {
            "C": 1.0,
            "kernel": "rbf",
            "gamma": "scale",
            "probability": True,
            "random_state": DEFAULT_RANDOM_STATE,
        },
    },
    "random_forest": {
        "model_class": "RandomForestClassifier",
        "description": "Random Forest ensemble of 100 decision trees",
        "params": {
            "n_estimators": 100,
            "max_depth": 5,
            "min_samples_split": 4,
            "random_state": DEFAULT_RANDOM_STATE,
        },
    },
}


def build_model(model_name: str, random_state: int = DEFAULT_RANDOM_STATE):
    """
    Instantiates a frozen classical candidate model.

    Parameters
    ----------
    model_name : str
        One of 'logistic_regression', 'svm_rbf', 'random_forest'.
    random_state : int, default=42
        Deterministic random seed.

    Returns
    -------
    BaseEstimator
        Configured scikit-learn estimator instance.
    """
    if model_name not in MODEL_CONFIGS:
        raise ValueError(f"Unknown model name '{model_name}'. Available: {list(MODEL_CONFIGS.keys())}")

    cfg = MODEL_CONFIGS[model_name]
    params = cfg["params"].copy()
    params["random_state"] = random_state

    if model_name == "logistic_regression":
        return LogisticRegression(**params)
    elif model_name == "svm_rbf":
        return SVC(**params)
    elif model_name == "random_forest":
        return RandomForestClassifier(**params)
    else:
        raise NotImplementedError(f"Model {model_name} is not implemented.")


def get_all_candidate_models(random_state: int = DEFAULT_RANDOM_STATE) -> Dict[str, Any]:
    """Returns a dictionary containing fresh instances of all candidate models."""
    return {
        name: build_model(name, random_state=random_state)
        for name in MODEL_CONFIGS
    }
