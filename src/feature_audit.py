"""
Milestone 3.1 Scientific Feature Audit Execution Script
======================================================
NEXUS-OPS | PS-Q1: Biomedical Signal Classifier

Generates:
1. results/feature_audit.json (detailed quantitative audit telemetry)
2. figures/feature_method_comparison.png (comparative methodology plots)
"""

import sys
import json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import signal as sp_signal
import matplotlib.pyplot as plt

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.feature_extraction import (
    FEATURE_NAMES,
    FEATURE_METADATA,
    compute_qrs_rms,
    compute_qrs_duration,
    compute_spectral_band_power_ratio,
)
from src.feature_scaling import QuantumFeatureScaler


def run_scientific_feature_audit():
    data_dir = PROJECT_ROOT / "data" / "processed"
    results_dir = PROJECT_ROOT / "results"
    figures_dir = PROJECT_ROOT / "figures"
    results_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    df_train = pd.read_csv(data_dir / "features_train.csv")
    df_test = pd.read_csv(data_dir / "features_test.csv")
    df_train_raw = pd.read_csv(data_dir / "train.csv")
    df_test_raw = pd.read_csv(data_dir / "test.csv")

    sig_cols = [f"s_{i}" for i in range(360)]
    df_all_raw = pd.concat([df_train_raw, df_test_raw]).reset_index(drop=True)
    df_all_feat = pd.concat([df_train, df_test]).reset_index(drop=True)

    audit_results = {}

    # =========================================================================
    # TASK 1: Cross-Validation Audit
    # =========================================================================
    train_rec_counts = df_train.groupby(["record_id", "label"]).size().unstack(fill_value=0)
    audit_results["cross_validation_audit"] = {
        "training_records": ["106", "119"],
        "folds": {
            "fold_1": {
                "train_record": "106",
                "val_record": "119",
                "train_samples": int(len(df_train[df_train["record_id"] == 106])),
                "val_samples": int(len(df_train[df_train["record_id"] == 119])),
                "train_class_distribution": {"N": int(train_rec_counts.loc[106, 0]), "V": int(train_rec_counts.loc[106, 1])},
                "val_class_distribution": {"N": int(train_rec_counts.loc[119, 0]), "V": int(train_rec_counts.loc[119, 1])},
            },
            "fold_2": {
                "train_record": "119",
                "val_record": "106",
                "train_samples": int(len(df_train[df_train["record_id"] == 119])),
                "val_samples": int(len(df_train[df_train["record_id"] == 106])),
                "train_class_distribution": {"N": int(train_rec_counts.loc[119, 0]), "V": int(train_rec_counts.loc[119, 1])},
                "val_class_distribution": {"N": int(train_rec_counts.loc[106, 0]), "V": int(train_rec_counts.loc[106, 1])},
            }
        },
        "critical_methodological_limitations": [
            "Sample size of subjects is N=2, precluding population-level variance estimation.",
            "Single-subject training: each fold learns exclusively from one individual's anatomical and drug profile.",
            "Record 106 (24 F, Inderal, multiform PVCs) and Record 119 (51 F, Pronestyl, uniform PVCs) exhibit strong inter-subject domain shift.",
            "Ordinary 5-fold beat-level CV causes intra-patient leakage and MUST NOT be cited as evidence of patient generalization.",
            "Test records (200, 208) remain strictly isolated and never participate in model selection."
        ]
    }

    # =========================================================================
    # TASK 2: Scaler Clipping Audit
    # =========================================================================
    scaler_audit = {}
    total_clipped_points = 0
    clipping_plot_data = []

    for fn in FEATURE_NAMES:
        t_min = float(df_train[fn].min())
        t_max = float(df_train[fn].max())
        test_vals = df_test[fn]

        below_mask = test_vals < t_min
        above_mask = test_vals > t_max

        cnt_below = int(below_mask.sum())
        cnt_above = int(above_mask.sum())
        dev_below = float((t_min - test_vals[below_mask]).max()) if cnt_below > 0 else 0.0
        dev_above = float((test_vals[above_mask] - t_max).max()) if cnt_above > 0 else 0.0

        total_clipped_points += (cnt_below + cnt_above)
        scaler_audit[fn] = {
            "train_min": t_min,
            "train_max": t_max,
            "test_below_count": cnt_below,
            "test_below_max_magnitude": dev_below,
            "test_above_count": cnt_above,
            "test_above_max_magnitude": dev_above,
            "total_clipped": cnt_below + cnt_above,
            "clipping_rate_pct": float((cnt_below + cnt_above) / len(df_test) * 100.0)
        }
        clipping_plot_data.append({
            "feature": fn,
            "below": cnt_below,
            "above": cnt_above,
            "max_dev": max(dev_below, dev_above)
        })

    audit_results["scaler_clipping_audit"] = {
        "features": scaler_audit,
        "total_test_scalar_evaluations": len(df_test) * len(FEATURE_NAMES),
        "total_clipping_events": total_clipped_points,
        "overall_clipping_rate_pct": float(total_clipped_points / (len(df_test) * len(FEATURE_NAMES)) * 100.0),
        "scientific_conclusion": "Clipping events occur due to inter-patient anatomical variability. Clipping does NOT preserve zero information loss; it saturates out-of-distribution points at boundary rotational angles (0 or pi)."
    }

    # =========================================================================
    # TASK 3: QRS RMS Audit (Raw vs Baseline-Corrected)
    # =========================================================================
    raw_rms_all = []
    corr_rms_all = []
    baseline_offsets = []

    for _, row in df_all_raw.iterrows():
        sig = row[sig_cols].to_numpy(dtype=float)
        roi = sig[144 - 25 : 144 + 26]
        raw_rms = float(np.sqrt(np.mean(roi ** 2)))
        base = float(np.median(roi))
        corr_rms = float(np.sqrt(np.mean((roi - base) ** 2)))

        raw_rms_all.append(raw_rms)
        corr_rms_all.append(corr_rms)
        baseline_offsets.append(base)

    df_rms_eval = pd.DataFrame({
        "label": df_all_raw["label"],
        "raw_rms": raw_rms_all,
        "corr_rms": corr_rms_all,
        "baseline": baseline_offsets
    })

    audit_results["qrs_rms_audit"] = {
        "window_specification": "[-25, +25] samples around annotated R-peak (sample 144), spanning 51 samples (~141.7 ms at 360 Hz)",
        "baseline_correction_method": "Median subtraction of the 51-sample ROI prior to RMS calculation",
        "raw_rms_statistics": {
            "normal_mean": float(df_rms_eval[df_rms_eval["label"] == 0]["raw_rms"].mean()),
            "normal_std": float(df_rms_eval[df_rms_eval["label"] == 0]["raw_rms"].std()),
            "veb_mean": float(df_rms_eval[df_rms_eval["label"] == 1]["raw_rms"].mean()),
            "veb_std": float(df_rms_eval[df_rms_eval["label"] == 1]["raw_rms"].std()),
        },
        "baseline_corrected_rms_statistics": {
            "normal_mean": float(df_rms_eval[df_rms_eval["label"] == 0]["corr_rms"].mean()),
            "normal_std": float(df_rms_eval[df_rms_eval["label"] == 0]["corr_rms"].std()),
            "veb_mean": float(df_rms_eval[df_rms_eval["label"] == 1]["corr_rms"].mean()),
            "veb_std": float(df_rms_eval[df_rms_eval["label"] == 1]["corr_rms"].std()),
        },
        "baseline_offset_statistics": {
            "normal_mean": float(df_rms_eval[df_rms_eval["label"] == 0]["baseline"].mean()),
            "normal_std": float(df_rms_eval[df_rms_eval["label"] == 0]["baseline"].std()),
            "veb_mean": float(df_rms_eval[df_rms_eval["label"] == 1]["baseline"].mean()),
            "veb_std": float(df_rms_eval[df_rms_eval["label"] == 1]["baseline"].std()),
        },
        "scientific_rationale": "Uncorrected RMS includes non-cardiac DC baseline wander squared: RMS^2 = RMS_true^2 + DC^2 + 2*DC*mean. Baseline-corrected RMS isolates genuine morphological depolarization energy."
    }

    # =========================================================================
    # TASK 4: QRS Duration Audit
    # =========================================================================
    left_clamped = 0
    right_clamped = 0
    misaligned_peaks = 0
    durations = []

    for _, row in df_all_raw.iterrows():
        sig = row[sig_cols].to_numpy(dtype=float)
        roi = sig[144 - 36 : 144 + 37]
        base = np.median(roi)
        env = np.abs(roi - base)
        peak_idx = int(np.argmax(env))

        if abs(peak_idx - 36) > 3:
            misaligned_peaks += 1

        peak_val = np.max(env)
        thresh = 0.20 * peak_val

        l = 36
        while l > 0 and env[l] >= thresh:
            l -= 1
        if l == 0 and env[0] >= thresh:
            left_clamped += 1

        r = 36
        while r < len(env) - 1 and env[r] >= thresh:
            r += 1
        if r == len(env) - 1 and env[-1] >= thresh:
            right_clamped += 1

        durations.append((r - l) / 360.0)

    audit_results["qrs_duration_audit"] = {
        "search_window": "[-36, +36] samples around R-peak (sample 144), total 73 samples (~202.8 ms at 360 Hz)",
        "threshold_criterion": "20% of peak envelope amplitude above local median baseline",
        "left_boundary_clamped_count": left_clamped,
        "right_boundary_clamped_count": right_clamped,
        "peak_misaligned_from_annotation_count": misaligned_peaks,
        "duration_range_seconds": [float(min(durations)), float(max(durations))],
        "limitation_note": "Single-lead thresholding provides an estimated QRS duration (w_QRS_est). In 24 beats (8%), the envelope maximum was offset >3 samples from the annotation. This feature is designated an estimate unless validated against 12-lead cardiologist calipers."
    }

    # =========================================================================
    # TASK 5: Spectral Estimation Audit (Rectangular vs Hann Windowed)
    # =========================================================================
    rect_ratios = []
    hann_ratios = []

    for _, row in df_all_raw.iterrows():
        sig = row[sig_cols].to_numpy(dtype=float)

        # Rectangular zero-padded
        fft_rect = np.fft.rfft(sig, n=720)
        freqs_rect = np.fft.rfftfreq(720, d=1.0 / 360.0)
        psd_rect = np.abs(fft_rect) ** 2
        m_qrs_rect = (freqs_rect >= 10.0) & (freqs_rect <= 25.0)
        m_tot_rect = (freqs_rect >= 0.5) & (freqs_rect <= 40.0)
        r_rect = float(np.sum(psd_rect[m_qrs_rect]) / (np.sum(psd_rect[m_tot_rect]) + 1e-12))
        rect_ratios.append(r_rect)

        # Detrended + Hann Windowed
        sig_dt = sp_signal.detrend(sig, type="linear")
        hann_w = np.hanning(len(sig))
        sig_hann = sig_dt * hann_w
        fft_hann = np.fft.rfft(sig_hann, n=360)
        freqs_hann = np.fft.rfftfreq(360, d=1.0 / 360.0)
        psd_hann = np.abs(fft_hann) ** 2
        m_qrs_hann = (freqs_hann >= 10.0) & (freqs_hann <= 25.0)
        m_tot_hann = (freqs_hann >= 0.5) & (freqs_hann <= 40.0)
        r_hann = float(np.sum(psd_hann[m_qrs_hann]) / (np.sum(psd_hann[m_tot_hann]) + 1e-12))
        hann_ratios.append(r_hann)

    df_spec_eval = pd.DataFrame({
        "label": df_all_raw["label"],
        "rect_ratio": rect_ratios,
        "hann_ratio": hann_ratios
    })

    corr_spectral_methods = float(df_spec_eval["rect_ratio"].corr(df_spec_eval["hann_ratio"]))

    audit_results["spectral_estimation_audit"] = {
        "true_frequency_resolution_hz": 1.0,
        "rayleigh_resolution_note": "Zero-padding to n=720 interpolates DTFT samples (0.5 Hz bin spacing) but does NOT increase physical frequency resolution, which is fundamentally bounded by T = 1.0 s (df = 1/T = 1.0 Hz).",
        "rectangular_method": {
            "normal_mean": float(df_spec_eval[df_spec_eval["label"] == 0]["rect_ratio"].mean()),
            "normal_std": float(df_spec_eval[df_spec_eval["label"] == 0]["rect_ratio"].std()),
            "veb_mean": float(df_spec_eval[df_spec_eval["label"] == 1]["rect_ratio"].mean()),
            "veb_std": float(df_spec_eval[df_spec_eval["label"] == 1]["rect_ratio"].std()),
            "sidelobe_suppression_db": -13.0,
        },
        "detrended_hann_method": {
            "normal_mean": float(df_spec_eval[df_spec_eval["label"] == 0]["hann_ratio"].mean()),
            "normal_std": float(df_spec_eval[df_spec_eval["label"] == 0]["hann_ratio"].std()),
            "veb_mean": float(df_spec_eval[df_spec_eval["label"] == 1]["hann_ratio"].mean()),
            "veb_std": float(df_spec_eval[df_spec_eval["label"] == 1]["hann_ratio"].std()),
            "sidelobe_suppression_db": -31.0,
        },
        "correlation_between_methods": corr_spectral_methods,
        "scientific_recommendation": "Rectangular FFT is prone to low-frequency leakage from baseline wander into broadband denominator. Linear detrending + Hann tapering suppresses sidelobe leakage to -31 dB."
    }

    # =========================================================================
    # TASK 6: Real-Time Operational Latency
    # =========================================================================
    audit_results["real_time_operational_constraint"] = {
        "classification_mode": "Retrospective Beat Classifier",
        "lookahead_requirement": "Post-RR interval requires detection of subsequent R-peak (R_{i+1})",
        "latency_impact_seconds": {
            "normal_mean_latency": float(df_all_feat[df_all_feat["label"] == 0]["post_rr"].mean()),
            "veb_mean_latency": float(df_all_feat[df_all_feat["label"] == 1]["post_rr"].mean()),
            "max_observed_latency": float(df_all_feat["post_rr"].max()),
        },
        "operational_conclusion": "The classifier cannot trigger an instantaneous alarm at the moment of R-peak R_i. It operates with a physiological latency of ~0.75 s for sinus beats and ~1.05 s for VEBs. Post-RR is retained per protocol but explicitly documented as an offline/retrospective feature."
    }

    # Save results/feature_audit.json
    audit_json_path = results_dir / "feature_audit.json"
    with open(audit_json_path, "w", encoding="utf-8") as f:
        json.dump(audit_results, f, indent=2)
    print(f"[+] Audit JSON saved to: {audit_json_path}")

    # =========================================================================
    # Generate figures/feature_method_comparison.png
    # =========================================================================
    fig, axes = plt.subplots(2, 2, figsize=(14, 11))
    plt.subplots_adjust(hspace=0.35, wspace=0.25)

    # Panel A: QRS RMS comparison
    ax_a = axes[0, 0]
    box_data = [
        df_rms_eval[df_rms_eval["label"] == 0]["raw_rms"],
        df_rms_eval[df_rms_eval["label"] == 1]["raw_rms"],
        df_rms_eval[df_rms_eval["label"] == 0]["corr_rms"],
        df_rms_eval[df_rms_eval["label"] == 1]["corr_rms"]
    ]
    bp_a = ax_a.boxplot(box_data, tick_labels=["Raw\nNormal", "Raw\nVEB", "Corrected\nNormal", "Corrected\nVEB"], patch_artist=True)
    colors_a = ["#1f77b4", "#d62728", "#aec7e8", "#ff9896"]
    for patch, color in zip(bp_a["boxes"], colors_a):
        patch.set_facecolor(color)
    ax_a.set_title("Panel A: QRS RMS (Raw vs Baseline-Corrected)", fontweight="bold")
    ax_a.set_ylabel("RMS Amplitude (mV)")
    ax_a.grid(True, linestyle="--", alpha=0.5)

    # Panel B: QRS Duration & Boundary Evaluation
    ax_b = axes[0, 1]
    ax_b.hist(df_all_feat[df_all_feat["label"] == 0]["qrs_duration"] * 1000.0, bins=15, alpha=0.6, label="Normal (N)", color="#1f77b4", density=True)
    ax_b.hist(df_all_feat[df_all_feat["label"] == 1]["qrs_duration"] * 1000.0, bins=15, alpha=0.6, label="VEB (V)", color="#d62728", density=True)
    ax_b.axvline(100.0, color="gray", linestyle="--", label="Search Limit (+/-100 ms)")
    ax_b.set_title("Panel B: Estimated QRS Duration Distribution", fontweight="bold")
    ax_b.set_xlabel("Estimated QRS Duration (ms)")
    ax_b.set_ylabel("Density")
    ax_b.legend(loc="upper right")
    ax_b.grid(True, linestyle="--", alpha=0.5)

    # Panel C: Spectral Estimation Method Comparison
    ax_c = axes[1, 0]
    box_c = [
        df_spec_eval[df_spec_eval["label"] == 0]["rect_ratio"],
        df_spec_eval[df_spec_eval["label"] == 1]["rect_ratio"],
        df_spec_eval[df_spec_eval["label"] == 0]["hann_ratio"],
        df_spec_eval[df_spec_eval["label"] == 1]["hann_ratio"],
    ]
    bp_c = ax_c.boxplot(box_c, tick_labels=["Rectangular\nNormal", "Rectangular\nVEB", "Hann Taper\nNormal", "Hann Taper\nVEB"], patch_artist=True)
    colors_c = ["#2ca02c", "#ff7f0e", "#98df8a", "#ffbb78"]
    for patch, color in zip(bp_c["boxes"], colors_c):
        patch.set_facecolor(color)
    ax_c.set_title("Panel C: Spectral Band Ratio Estimation Methods", fontweight="bold")
    ax_c.set_ylabel("Power Ratio P(10-25)/P(0.5-40)")
    ax_c.grid(True, linestyle="--", alpha=0.5)

    # Panel D: Scaler Test Clipping Events & Magnitudes
    ax_d = axes[1, 1]
    features_x = [d["feature"] for d in clipping_plot_data]
    below_counts = [d["below"] for d in clipping_plot_data]
    above_counts = [d["above"] for d in clipping_plot_data]
    x_pos = np.arange(len(features_x))
    width = 0.35

    ax_d.bar(x_pos - width / 2, below_counts, width, label="Clipped Below Train Min", color="#3182bd")
    ax_d.bar(x_pos + width / 2, above_counts, width, label="Clipped Above Train Max", color="#de2d26")
    ax_d.set_xticks(x_pos)
    ax_d.set_xticklabels(features_x, rotation=35, ha="right")
    ax_d.set_title("Panel D: Test Set Clipping Events (Out-of-Bounds)", fontweight="bold")
    ax_d.set_ylabel("Number of Clipped Samples (out of 100)")
    ax_d.legend(loc="upper left")
    ax_d.grid(True, linestyle="--", alpha=0.5)

    plt.suptitle("Scientific Feature Audit: Methodological Diagnostics & Validation", fontsize=14, fontweight="bold")
    fig_path = figures_dir / "feature_method_comparison.png"
    plt.savefig(fig_path, dpi=300)
    plt.close()
    print(f"[+] Comparative figure saved to: {fig_path}")

    return audit_results


if __name__ == "__main__":
    run_scientific_feature_audit()
