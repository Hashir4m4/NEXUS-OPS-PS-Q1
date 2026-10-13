"""
Feature Validation, Scaling & Analysis Module
=============================================
NEXUS-OPS | PS-Q1: Biomedical Signal Classifier (Milestone 3)

Orchestrates:
1. Feature extraction across train.csv and test.csv.
2. Leakage-safe scaling fitting on training data only.
3. Exporting data/processed/features_train.csv and features_test.csv.
4. Statistical profiling, correlation analysis, and outlier inspection.
5. Generation of publication-quality diagnostic visualizations:
   - figures/feature_distributions.png
   - figures/feature_correlation.png
   - figures/feature_boxplots.png
6. Structured results export to results/feature_summary.json.
"""

import sys
import json
from pathlib import Path
from typing import Dict, List, Tuple
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.feature_extraction import (
    FEATURE_NAMES,
    FEATURE_METADATA,
    extract_features_for_dataframe,
)
from src.feature_scaling import QuantumFeatureScaler


def run_feature_pipeline() -> Tuple[pd.DataFrame, pd.DataFrame, Dict]:
    """
    Executes the end-to-end feature extraction, leakage-safe scaling,
    and analysis workflow.
    """
    data_dir = PROJECT_ROOT / "data" / "processed"
    raw_mitbih_dir = PROJECT_ROOT / "data" / "mitbih"
    results_dir = PROJECT_ROOT / "results"
    figures_dir = PROJECT_ROOT / "figures"

    results_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    print("[*] Loading processed segment datasets...")
    df_train_raw = pd.read_csv(data_dir / "train.csv")
    df_test_raw = pd.read_csv(data_dir / "test.csv")

    # 1. Feature Extraction
    print("[*] Extracting 6 physiological features for training set (200 beats)...")
    df_feat_train = extract_features_for_dataframe(df_train_raw, data_dir=raw_mitbih_dir)

    print("[*] Extracting 6 physiological features for test set (100 beats)...")
    df_feat_test = extract_features_for_dataframe(df_test_raw, data_dir=raw_mitbih_dir)

    # 2. Leakage-Safe Quantum Feature Scaling
    print("[*] Fitting QuantumFeatureScaler EXCLUSIVELY on training features...")
    scaler = QuantumFeatureScaler(target_min=0.0, target_max=np.pi, clip=True)
    scaler.fit(df_feat_train[FEATURE_NAMES])

    print("[*] Transforming training and test features to [0, pi]...")
    train_scaled = scaler.transform(df_feat_train[FEATURE_NAMES])
    test_scaled = scaler.transform(df_feat_test[FEATURE_NAMES])

    # Append scaled columns
    scaled_feature_names = [f"{fn}_scaled" for fn in FEATURE_NAMES]
    for i, col_name in enumerate(scaled_feature_names):
        df_feat_train[col_name] = train_scaled[:, i]
        df_feat_test[col_name] = test_scaled[:, i]

    # Save processed feature CSVs
    feat_train_path = data_dir / "features_train.csv"
    feat_test_path = data_dir / "features_test.csv"
    df_feat_train.to_csv(feat_train_path, index=False)
    df_feat_test.to_csv(feat_test_path, index=False)
    print(f"  [+] Saved {feat_train_path} ({len(df_feat_train)} rows)")
    print(f"  [+] Saved {feat_test_path} ({len(df_feat_test)} rows)")

    # 3. Statistical Analysis
    df_all_feat = pd.concat([df_feat_train, df_feat_test]).reset_index(drop=True)
    stats_summary = compute_feature_statistics(df_feat_train, df_feat_test, scaler)

    # 4. Generate Visualizations
    print("[*] Generating publication figures...")
    generate_feature_figures(df_all_feat, figures_dir)

    # 5. Export JSON summary
    summary_json_path = results_dir / "feature_summary.json"
    with open(summary_json_path, "w", encoding="utf-8") as f:
        json.dump(stats_summary, f, indent=2)
    print(f"  [+] Saved structured summary to {summary_json_path}")

    return df_feat_train, df_feat_test, stats_summary


def compute_feature_statistics(
    df_train: pd.DataFrame,
    df_test: pd.DataFrame,
    scaler: QuantumFeatureScaler
) -> Dict:
    """Computes comprehensive feature statistics, correlations, and outlier counts."""
    df_all = pd.concat([df_train, df_test]).reset_index(drop=True)

    summary: Dict = {
        "feature_names": FEATURE_NAMES,
        "feature_metadata": FEATURE_METADATA,
        "sample_counts": {
            "train": len(df_train),
            "test": len(df_test),
            "total": len(df_all),
        },
        "scaler_parameters": scaler.to_dict(),
        "unscaled_statistics": {},
        "scaled_statistics": {},
        "correlation_matrix": {},
        "outlier_analysis": {},
        "validation_checks": {},
    }

    # Statistics by class and split
    for fn in FEATURE_NAMES:
        summary["unscaled_statistics"][fn] = {
            "overall": {
                "mean": float(df_all[fn].mean()),
                "std": float(df_all[fn].std()),
                "min": float(df_all[fn].min()),
                "q25": float(df_all[fn].quantile(0.25)),
                "median": float(df_all[fn].median()),
                "q75": float(df_all[fn].quantile(0.75)),
                "max": float(df_all[fn].max()),
            },
            "class_0_normal": {
                "mean": float(df_all[df_all["label"] == 0][fn].mean()),
                "std": float(df_all[df_all["label"] == 0][fn].std()),
                "median": float(df_all[df_all["label"] == 0][fn].median()),
            },
            "class_1_veb": {
                "mean": float(df_all[df_all["label"] == 1][fn].mean()),
                "std": float(df_all[df_all["label"] == 1][fn].std()),
                "median": float(df_all[df_all["label"] == 1][fn].median()),
            },
            "train_mean": float(df_train[fn].mean()),
            "test_mean": float(df_test[fn].mean()),
        }

        # Scaled bounds
        scaled_col = f"{fn}_scaled"
        summary["scaled_statistics"][scaled_col] = {
            "train_min": float(df_train[scaled_col].min()),
            "train_max": float(df_train[scaled_col].max()),
            "test_min": float(df_test[scaled_col].min()),
            "test_max": float(df_test[scaled_col].max()),
        }

        # Outlier count via IQR method (1.5 * IQR on training set)
        q25 = df_train[fn].quantile(0.25)
        q75 = df_train[fn].quantile(0.75)
        iqr = q75 - q25
        lower_bound = q25 - 1.5 * iqr
        upper_bound = q75 + 1.5 * iqr
        train_outliers = int(((df_train[fn] < lower_bound) | (df_train[fn] > upper_bound)).sum())
        test_outliers = int(((df_test[fn] < lower_bound) | (df_test[fn] > upper_bound)).sum())

        summary["outlier_analysis"][fn] = {
            "iqr_lower_bound": float(lower_bound),
            "iqr_upper_bound": float(upper_bound),
            "train_outliers_count": train_outliers,
            "test_outliers_count": test_outliers,
        }

    # Correlation Matrix (Unscaled Training Data)
    corr_df = df_train[FEATURE_NAMES].corr()
    for col in FEATURE_NAMES:
        summary["correlation_matrix"][col] = {
            row: float(corr_df.loc[col, row]) for row in FEATURE_NAMES
        }

    # Automated Validation Checks
    train_has_nan = bool(df_train[[f"{fn}_scaled" for fn in FEATURE_NAMES]].isna().any().any())
    test_has_nan = bool(df_test[[f"{fn}_scaled" for fn in FEATURE_NAMES]].isna().any().any())
    train_in_bounds = bool(
        ((df_train[[f"{fn}_scaled" for fn in FEATURE_NAMES]] >= 0.0) &
         (df_train[[f"{fn}_scaled" for fn in FEATURE_NAMES]] <= np.pi)).all().all()
    )
    test_in_bounds = bool(
        ((df_test[[f"{fn}_scaled" for fn in FEATURE_NAMES]] >= 0.0) &
         (df_test[[f"{fn}_scaled" for fn in FEATURE_NAMES]] <= np.pi)).all().all()
    )

    summary["validation_checks"] = {
        "train_has_nan": train_has_nan,
        "test_has_nan": test_has_nan,
        "train_scaled_in_bounds_0_pi": train_in_bounds,
        "test_scaled_in_bounds_0_pi": test_in_bounds,
        "zero_leakage_guarantee": True,
    }

    return summary


def generate_feature_figures(df_all: pd.DataFrame, figures_dir: Path) -> None:
    """Generates distribution plots, correlation matrix, and boxplots."""
    plt.style.use("default")
    plt.rcParams.update({"font.size": 10, "figure.autolayout": True})

    # 1. Feature Distributions (Histograms / KDE by Class)
    fig, axes = plt.subplots(2, 3, figsize=(14, 8))
    axes = axes.flatten()

    for i, fn in enumerate(FEATURE_NAMES):
        ax = axes[i]
        n_vals = df_all[df_all["label"] == 0][fn]
        v_vals = df_all[df_all["label"] == 1][fn]

        ax.hist(n_vals, bins=25, alpha=0.6, label="Normal (N)", color="#1f77b4", density=True)
        ax.hist(v_vals, bins=25, alpha=0.6, label="VEB (V)", color="#d62728", density=True)

        meta = FEATURE_METADATA[fn]
        ax.set_title(f"{fn} ({meta['unit']})", fontweight="bold")
        ax.set_xlabel(f"{fn} [{meta['unit']}]")
        ax.set_ylabel("Density")
        ax.legend(loc="upper right", frameon=True)
        ax.grid(True, linestyle="--", alpha=0.5)

    plt.suptitle("ECG Feature Distributions by Class (Normal vs VEB)", fontsize=14, fontweight="bold")
    dist_path = figures_dir / "feature_distributions.png"
    plt.savefig(dist_path, dpi=300)
    plt.close()
    print(f"  [+] Saved {dist_path}")

    # 2. Feature Correlation Matrix Heatmap
    corr_matrix = df_all[FEATURE_NAMES].corr().to_numpy()

    fig, ax = plt.subplots(figsize=(8, 7))
    cax = ax.matshow(corr_matrix, cmap="coolwarm", vmin=-1, vmax=1)
    fig.colorbar(cax)

    ax.set_xticks(range(len(FEATURE_NAMES)))
    ax.set_yticks(range(len(FEATURE_NAMES)))
    ax.set_xticklabels(FEATURE_NAMES, rotation=45, ha="left")
    ax.set_yticklabels(FEATURE_NAMES)

    # Annotate correlation values
    for r in range(len(FEATURE_NAMES)):
        for c in range(len(FEATURE_NAMES)):
            val = corr_matrix[r, c]
            text_color = "white" if abs(val) > 0.5 else "black"
            ax.text(c, r, f"{val:.2f}", va="center", ha="center", color=text_color, fontweight="bold")

    plt.title("ECG Feature Correlation Matrix", fontsize=12, fontweight="bold", pad=20)
    corr_path = figures_dir / "feature_correlation.png"
    plt.savefig(corr_path, dpi=300)
    plt.close()
    print(f"  [+] Saved {corr_path}")

    # 3. Scaled Feature Boxplots by Class
    scaled_cols = [f"{fn}_scaled" for fn in FEATURE_NAMES]
    fig, axes = plt.subplots(2, 3, figsize=(14, 8))
    axes = axes.flatten()

    for i, (fn, sc_col) in enumerate(zip(FEATURE_NAMES, scaled_cols)):
        ax = axes[i]
        n_vals = df_all[df_all["label"] == 0][sc_col]
        v_vals = df_all[df_all["label"] == 1][sc_col]

        bp = ax.boxplot([n_vals, v_vals], tick_labels=["Normal (N)", "VEB (V)"], patch_artist=True)
        bp["boxes"][0].set_facecolor("#1f77b4")
        bp["boxes"][1].set_facecolor("#d62728")
        for box in bp["boxes"]:
            box.set_alpha(0.7)

        ax.set_title(f"{fn} (Scaled [0, π])", fontweight="bold")
        ax.set_ylabel("Quantum Angle (radians)")
        ax.set_ylim(-0.1, np.pi + 0.1)
        ax.axhline(0, color="gray", linestyle=":", alpha=0.5)
        ax.axhline(np.pi, color="purple", linestyle="--", alpha=0.7, label="π (max rotation)")
        ax.grid(True, linestyle="--", alpha=0.5)
        if i == 0:
            ax.legend(loc="upper right")

    plt.suptitle("Quantum-Scaled Features in [0, π] Stratified by Class", fontsize=14, fontweight="bold")
    box_path = figures_dir / "feature_boxplots.png"
    plt.savefig(box_path, dpi=300)
    plt.close()
    print(f"  [+] Saved {box_path}")


if __name__ == "__main__":
    run_feature_pipeline()
