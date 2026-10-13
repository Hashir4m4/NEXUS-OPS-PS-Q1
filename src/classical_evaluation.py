"""
Classical Machine Learning Evaluation Module
============================================
NEXUS-OPS | PS-Q1: Biomedical Signal Classifier (Milestone 4)

Executes:
1. Patient-level Leave-One-Record-Out (LORO) cross-validation across training records 106 and 119.
2. Preprocessing isolation per fold (scalers fitted exclusively on the active training fold).
3. Final evaluation on independent held-out test records 200 and 208.
4. Comprehensive metric calculation: Accuracy, Sensitivity (Recall), Specificity, Precision, F1, ROC-AUC.
5. Extraction of model interpretability signals: Logistic Regression weights and Random Forest importances.
6. Generation of diagnostic plots and structured JSON results.
"""

import sys
import json
from pathlib import Path
from typing import Dict, List, Tuple, Any
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    confusion_matrix,
    classification_report,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.feature_extraction import FEATURE_NAMES, FEATURE_METADATA
from src.feature_scaling import QuantumFeatureScaler
from src.classical_models import get_all_candidate_models, MODEL_CONFIGS, DEFAULT_RANDOM_STATE


def compute_binary_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_prob: np.ndarray
) -> Dict[str, Any]:
    """
    Computes standard biomedical binary classification metrics:
    Positive class (1) = Ventricular Ectopic Beat (VEB / 'V')
    Negative class (0) = Normal Sinus Beat ('N')
    """
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
    tn, fp, fn, tp = cm.ravel()

    # Medical sensitivity and specificity
    sensitivity = float(tp / (tp + fn)) if (tp + fn) > 0 else 0.0
    specificity = float(tn / (tn + fp)) if (tn + fp) > 0 else 0.0
    accuracy = float(accuracy_score(y_true, y_pred))
    precision = float(precision_score(y_true, y_pred, zero_division=0))
    f1 = float(f1_score(y_true, y_pred, zero_division=0))

    try:
        auc = float(roc_auc_score(y_true, y_prob))
    except Exception:
        auc = 0.5

    return {
        "accuracy": accuracy,
        "sensitivity": sensitivity,  # Recall for class 1
        "specificity": specificity,  # Recall for class 0
        "precision": precision,
        "f1_score": f1,
        "roc_auc": auc,
        "confusion_matrix": {
            "tn": int(tn),
            "fp": int(fp),
            "fn": int(fn),
            "tp": int(tp),
            "matrix": [[int(tn), int(fp)], [int(fn), int(tp)]],
        },
    }


def evaluate_loro_validation(df_train: pd.DataFrame) -> Dict[str, Any]:
    """
    Performs patient-level Leave-One-Record-Out (LORO) cross-validation
    across the two training subjects (Records 106 and 119).
    """
    print("\n[*] Starting Patient-Level Leave-One-Record-Out (LORO) Validation...")
    loro_results = {"folds": {}, "summary": {}}

    folds = [
        {"fold_id": "fold_1", "train_rec": 106, "val_rec": 119},
        {"fold_id": "fold_2", "train_rec": 119, "val_rec": 106},
    ]

    for f_info in folds:
        fid = f_info["fold_id"]
        tr_rec = f_info["train_rec"]
        val_rec = f_info["val_rec"]

        train_sub = df_train[df_train["record_id"] == tr_rec].copy()
        val_sub = df_train[df_train["record_id"] == val_rec].copy()

        # Strict preprocessing isolation: fit scaler exclusively on active training record
        scaler = QuantumFeatureScaler(clip=True)
        scaler.fit(train_sub[FEATURE_NAMES])

        X_tr = scaler.transform(train_sub[FEATURE_NAMES])
        y_tr = train_sub["label"].to_numpy(dtype=int)

        X_val = scaler.transform(val_sub[FEATURE_NAMES])
        y_val = val_sub["label"].to_numpy(dtype=int)

        loro_results["folds"][fid] = {
            "train_record": str(tr_rec),
            "val_record": str(val_rec),
            "train_samples": len(X_tr),
            "val_samples": len(X_val),
            "train_class_balance": {"N": int((y_tr == 0).sum()), "V": int((y_tr == 1).sum())},
            "val_class_balance": {"N": int((y_val == 0).sum()), "V": int((y_val == 1).sum())},
            "models": {},
        }

        models = get_all_candidate_models(random_state=DEFAULT_RANDOM_STATE)
        print(f"  --- {fid.upper()} (Train: Rec {tr_rec} | Val: Rec {val_rec}) ---")

        for m_name, model in models.items():
            model.fit(X_tr, y_tr)
            y_pred = model.predict(X_val)
            y_prob = model.predict_proba(X_val)[:, 1] if hasattr(model, "predict_proba") else y_pred

            metrics = compute_binary_metrics(y_val, y_pred, y_prob)
            loro_results["folds"][fid]["models"][m_name] = metrics

            print(f"    {m_name:20s}: Acc={metrics['accuracy']:.4f} | Sens={metrics['sensitivity']:.4f} | Spec={metrics['specificity']:.4f} | F1={metrics['f1_score']:.4f} | AUC={metrics['roc_auc']:.4f}")

    # Compute mean metrics across the two folds
    for m_name in MODEL_CONFIGS:
        accs = [loro_results["folds"][f["fold_id"]]["models"][m_name]["accuracy"] for f in folds]
        sens = [loro_results["folds"][f["fold_id"]]["models"][m_name]["sensitivity"] for f in folds]
        specs = [loro_results["folds"][f["fold_id"]]["models"][m_name]["specificity"] for f in folds]
        f1s = [loro_results["folds"][f["fold_id"]]["models"][m_name]["f1_score"] for f in folds]
        aucs = [loro_results["folds"][f["fold_id"]]["models"][m_name]["roc_auc"] for f in folds]

        loro_results["summary"][m_name] = {
            "mean_accuracy": float(np.mean(accs)),
            "std_accuracy": float(np.std(accs)),
            "mean_sensitivity": float(np.mean(sens)),
            "std_sensitivity": float(np.std(sens)),
            "mean_specificity": float(np.mean(specs)),
            "std_specificity": float(np.std(specs)),
            "mean_f1_score": float(np.mean(f1s)),
            "mean_roc_auc": float(np.mean(aucs)),
        }

    return loro_results


def evaluate_final_test_set(
    df_train: pd.DataFrame,
    df_test: pd.DataFrame
) -> Dict[str, Any]:
    """
    Evaluates frozen candidate models once on independent test records 200 and 208.
    """
    print("\n[*] Starting Final Test Evaluation on Records 200 & 208...")
    test_results = {"models": {}, "interpretability": {}}

    # Preprocessing: Fit scaler on complete training cohort (Records 106 & 119)
    scaler = QuantumFeatureScaler(clip=True)
    scaler.fit(df_train[FEATURE_NAMES])

    X_train = scaler.transform(df_train[FEATURE_NAMES])
    y_train = df_train["label"].to_numpy(dtype=int)

    X_test = scaler.transform(df_test[FEATURE_NAMES])
    y_test = df_test["label"].to_numpy(dtype=int)

    models = get_all_candidate_models(random_state=DEFAULT_RANDOM_STATE)

    for m_name, model in models.items():
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)
        y_prob = model.predict_proba(X_test)[:, 1] if hasattr(model, "predict_proba") else y_pred

        metrics = compute_binary_metrics(y_test, y_pred, y_prob)
        clf_rep = classification_report(y_test, y_pred, target_names=["Normal", "VEB"], output_dict=True)
        metrics["classification_report"] = clf_rep
        test_results["models"][m_name] = metrics

        print(f"  {m_name:20s}: Acc={metrics['accuracy']:.4f} | Sens={metrics['sensitivity']:.4f} | Spec={metrics['specificity']:.4f} | F1={metrics['f1_score']:.4f} | AUC={metrics['roc_auc']:.4f}")
        print(f"    Confusion Matrix: TN={metrics['confusion_matrix']['tn']}, FP={metrics['confusion_matrix']['fp']}, FN={metrics['confusion_matrix']['fn']}, TP={metrics['confusion_matrix']['tp']}")

        # Extract model interpretability signals
        if m_name == "logistic_regression":
            coefs = model.coef_[0]
            intercept = float(model.intercept_[0])
            test_results["interpretability"]["logistic_regression"] = {
                "intercept": intercept,
                "coefficients": {fn: float(c) for fn, c in zip(FEATURE_NAMES, coefs)},
                "odds_ratios": {fn: float(np.exp(c)) for fn, c in zip(FEATURE_NAMES, coefs)},
            }
        elif m_name == "random_forest":
            importances = model.feature_importances_
            test_results["interpretability"]["random_forest"] = {
                "feature_importances_gini": {fn: float(imp) for fn, imp in zip(FEATURE_NAMES, importances)}
            }

    return test_results


def generate_classical_figures(
    loro_results: Dict[str, Any],
    test_results: Dict[str, Any],
    figures_dir: Path
) -> None:
    """Generates confusion matrices and comparative bar plots."""
    plt.style.use("default")
    plt.rcParams.update({"font.size": 10, "figure.autolayout": True})

    # 1. Confusion Matrices Plot (Test Set)
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))
    model_keys = ["logistic_regression", "svm_rbf", "random_forest"]
    model_titles = ["Logistic Regression", "SVM (RBF Kernel)", "Random Forest"]

    for i, (m_key, title) in enumerate(zip(model_keys, model_titles)):
        ax = axes[i]
        cm = test_results["models"][m_key]["confusion_matrix"]["matrix"]
        cm_arr = np.array(cm)

        cax = ax.matshow(cm_arr, cmap="Blues", alpha=0.75)
        for r in range(2):
            for c in range(2):
                val = cm_arr[r, c]
                color = "white" if val > 25 else "black"
                ax.text(c, r, f"{val}", va="center", ha="center", fontsize=14, fontweight="bold", color=color)

        ax.set_xticks([0, 1])
        ax.set_yticks([0, 1])
        ax.set_xticklabels(["Pred: Normal (0)", "Pred: VEB (1)"])
        ax.set_yticklabels(["True: Normal (0)", "True: VEB (1)"])
        acc = test_results["models"][m_key]["accuracy"]
        f1 = test_results["models"][m_key]["f1_score"]
        ax.set_title(f"{title}\nAcc: {acc:.2f} | F1: {f1:.2f}", fontweight="bold", pad=12)

    plt.suptitle("Classical Baseline Test Confusion Matrices (Records 200 & 208)", fontsize=13, fontweight="bold")
    cm_path = figures_dir / "classical_confusion_matrices.png"
    plt.savefig(cm_path, dpi=300)
    plt.close()
    print(f"[+] Saved confusion matrices plot: {cm_path}")

    # 2. Performance Comparison Bar Chart (LORO vs Test)
    fig, ax = plt.subplots(figsize=(10, 6))
    metrics_to_plot = ["accuracy", "sensitivity", "specificity", "f1_score", "roc_auc"]
    metric_labels = ["Accuracy", "Sensitivity", "Specificity", "F1-Score", "ROC-AUC"]

    x = np.arange(len(metrics_to_plot))
    width = 0.25

    lr_vals = [test_results["models"]["logistic_regression"][m] for m in metrics_to_plot]
    svm_vals = [test_results["models"]["svm_rbf"][m] for m in metrics_to_plot]
    rf_vals = [test_results["models"]["random_forest"][m] for m in metrics_to_plot]

    rects1 = ax.bar(x - width, lr_vals, width, label="Logistic Regression", color="#1f77b4")
    rects2 = ax.bar(x, svm_vals, width, label="SVM (RBF)", color="#ff7f0e")
    rects3 = ax.bar(x + width, rf_vals, width, label="Random Forest", color="#2ca02c")

    ax.set_ylabel("Score (0.0 to 1.0)", fontweight="bold")
    ax.set_title("Classical Models Performance Comparison on Test Set (Records 200 & 208)", fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(metric_labels, fontweight="bold")
    ax.set_ylim(0.0, 1.1)
    ax.legend(loc="lower right")
    ax.grid(True, linestyle="--", alpha=0.5, axis="y")

    # Add text labels on bars
    for rects in [rects1, rects2, rects3]:
        for rect in rects:
            height = rect.get_height()
            ax.annotate(f"{height:.2f}",
                        xy=(rect.get_x() + rect.get_width() / 2, height),
                        xytext=(0, 3), textcoords="offset points",
                        ha="center", va="bottom", fontsize=8)

    comp_path = figures_dir / "classical_model_comparison.png"
    plt.savefig(comp_path, dpi=300)
    plt.close()
    print(f"[+] Saved model comparison plot: {comp_path}")


def run_classical_baseline_experiment() -> Dict[str, Any]:
    """Runs LORO validation, final test evaluation, and saves all outputs."""
    data_dir = PROJECT_ROOT / "data" / "processed"
    results_dir = PROJECT_ROOT / "results"
    figures_dir = PROJECT_ROOT / "figures"
    results_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    df_train = pd.read_csv(data_dir / "features_train.csv")
    df_test = pd.read_csv(data_dir / "features_test.csv")

    loro_results = evaluate_loro_validation(df_train)
    test_results = evaluate_final_test_set(df_train, df_test)

    # Package full baseline experiment artifact
    experiment_results = {
        "experiment_name": "Milestone_4_Classical_ML_Baselines",
        "dataset": {
            "train_samples": len(df_train),
            "test_samples": len(df_test),
            "train_records": [106, 119],
            "test_records": [200, 208],
            "features": FEATURE_NAMES,
            "classes": {"0": "Normal ('N')", "1": "VEB ('V')"},
        },
        "model_configurations": MODEL_CONFIGS,
        "leave_one_record_out_validation": loro_results,
        "final_test_evaluation": test_results,
    }

    # Save results/classical_baseline.json
    out_json = results_dir / "classical_baseline.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(experiment_results, f, indent=2)
    print(f"\n[+] Baseline results saved to: {out_json}")

    # Generate Figures
    generate_classical_figures(loro_results, test_results, figures_dir)

    return experiment_results


if __name__ == "__main__":
    run_classical_baseline_experiment()
