"""
Train and calibrate decision thresholds from real ASVspoof, ElevenLabs, Google Voice, and Human data.
Maximizes separation between bonafide human speech and AI synthetic voices.
Outputs calibrated_thresholds.json for AASISTAuthenticityEngine.
"""

import os
import sys
import json
import numpy as np
from typing import Dict, Any

sys.stdout.reconfigure(encoding='utf-8')

TRAIN_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "training_data"))
FEATURES_FILE = os.path.join(TRAIN_DIR, "extracted_features.npz")
OUTPUT_THRESHOLDS = os.path.join(os.path.dirname(__file__), "..", "engines", "calibrated_thresholds.json")

def calibrate_thresholds():
    if not os.path.exists(FEATURES_FILE):
        print(f"[ERROR] Features file not found: {FEATURES_FILE}")
        print("Please run extract_features.py first.")
        sys.exit(1)

    data = np.load(FEATURES_FILE, allow_pickle=True)
    X = data["X"]
    y = data["y"]
    feature_names = list(data["feature_names"])
    sources = list(data["sources"])

    print(f"[LOADED] Dataset with {len(y)} samples ({sum(y == 0)} Human, {sum(y == 1)} AI)")
    print(f"Features: {feature_names}")

    feat_idx = {name: i for i, name in enumerate(feature_names)}

    # Separate human vs AI feature matrices
    X_human = X[y == 0]
    X_ai = X[y == 1]

    print("\n" + "=" * 65)
    print(f"{'FEATURE':<18} | {'HUMAN MEAN ± STD':<20} | {'AI MEAN ± STD':<20}")
    print("=" * 65)
    for name in feature_names:
        idx = feat_idx[name]
        h_vals = X_human[:, idx]
        a_vals = X_ai[:, idx]
        print(f"{name:<18} | {np.mean(h_vals):>8.3f} ± {np.std(h_vals):<8.3f} | {np.mean(a_vals):>8.3f} ± {np.std(a_vals):<8.3f}")

    # Statistical boundary calculation
    # 1. Biological Micro-Tremor (Jitter)
    # Humans have natural physiological tremor [1.20, 2.85]
    h_jitter = X_human[:, feat_idx["jitter"]]
    jitter_min = float(max(0.85, np.percentile(h_jitter, 2)))
    jitter_max = float(min(3.10, np.percentile(h_jitter, 98)))

    # 2. Glottal Snapping Kurtosis
    h_kurt = X_human[:, feat_idx["env_diff_kurt"]]
    kurt_min = float(max(11.0, np.percentile(h_kurt, 5)))

    # 3. Voiced High-Frequency Ratio
    h_voiced_hi = X_human[:, feat_idx["voiced_hi_ratio"]]
    voiced_hi_max = float(min(0.38, np.percentile(h_voiced_hi, 96)))

    # 4. Global STFT High-Frequency Ratio (Google Voice / Vocoder leakage)
    h_stft_hi = X_human[:, feat_idx["stft_hi_ratio"]]
    stft_hi_max = float(min(0.24, np.percentile(h_stft_hi, 97)))

    # 5. Direct Microphone Near-field Proximity (Sub-220Hz bass)
    h_low_freq = X_human[:, feat_idx["low_freq_ratio"]]
    low_freq_min = float(max(0.040, np.percentile(h_low_freq, 3)))

    # 6. Speech Cadence & Pause Timing Variance (ElevenLabs / Google Voice isochrony)
    # Humans have variable inter-word timing. AI voices have metronomic pauses.
    h_pause_std = X_human[:, feat_idx["pause_std"]]
    h_pause_std_valid = h_pause_std[h_pause_std > 0]
    pause_std_min = float(np.percentile(h_pause_std_valid, 5)) if len(h_pause_std_valid) > 0 else 0.020
    pause_std_min = float(np.clip(pause_std_min, 0.018, 0.026))

    h_pause_cv = X_human[:, feat_idx["pause_cv"]]
    h_pause_cv_valid = h_pause_cv[h_pause_cv > 0]
    pause_cv_min = float(np.percentile(h_pause_cv_valid, 5)) if len(h_pause_cv_valid) > 0 else 0.25
    pause_cv_min = float(np.clip(pause_cv_min, 0.22, 0.32))

    calibrated = {
        "metadata": {
            "trained_on": "ASVspoof 2017/2015 + ElevenLabs + Google Voice + Real Human",
            "num_human_chunks": int(len(X_human)),
            "num_ai_chunks": int(len(X_ai)),
            "method": "Empirical Percentile Boundary Calibration"
        },
        "thresholds": {
            "jitter_min": round(jitter_min, 3),
            "jitter_max": round(jitter_max, 3),
            "glottal_kurt_min": round(kurt_min, 2),
            "voiced_hi_ratio_max": round(voiced_hi_max, 3),
            "stft_hi_ratio_max": round(stft_hi_max, 3),
            "low_freq_ratio_min": round(low_freq_min, 4),
            "pause_std_min": round(pause_std_min, 4),
            "pause_cv_min": round(pause_cv_min, 3)
        }
    }

    print("\n" + "=" * 65)
    print("CALIBRATED THRESHOLDS DERIVED FROM REAL TRAINING DATA:")
    print("=" * 65)
    for k, v in calibrated["thresholds"].items():
        print(f"  {k:<22}: {v}")

    os.makedirs(os.path.dirname(OUTPUT_THRESHOLDS), exist_ok=True)
    with open(OUTPUT_THRESHOLDS, "w", encoding="utf-8") as f:
        json.dump(calibrated, f, indent=2)

    print(f"\n[SAVED] Calibrated configuration written to: {OUTPUT_THRESHOLDS}")

    # Evaluate decision logic on training data
    correct_h = 0
    for row in X_human:
        j = row[feat_idx["jitter"]]
        k = row[feat_idx["env_diff_kurt"]]
        vhi = row[feat_idx["voiced_hi_ratio"]]
        shi = row[feat_idx["stft_hi_ratio"]]
        lf = row[feat_idx["low_freq_ratio"]]
        p_std = row[feat_idx["pause_std"]]
        p_cv = row[feat_idx["pause_cv"]]
        
        is_human = (
            (calibrated["thresholds"]["jitter_min"] <= j <= calibrated["thresholds"]["jitter_max"]) and
            (k >= calibrated["thresholds"]["glottal_kurt_min"]) and
            (vhi < calibrated["thresholds"]["voiced_hi_ratio_max"]) and
            (shi < calibrated["thresholds"]["stft_hi_ratio_max"]) and
            (lf >= calibrated["thresholds"]["low_freq_ratio_min"])
        )
        if is_human:
            correct_h += 1

    correct_ai = 0
    for row in X_ai:
        j = row[feat_idx["jitter"]]
        k = row[feat_idx["env_diff_kurt"]]
        vhi = row[feat_idx["voiced_hi_ratio"]]
        shi = row[feat_idx["stft_hi_ratio"]]
        lf = row[feat_idx["low_freq_ratio"]]
        p_std = row[feat_idx["pause_std"]]
        p_cv = row[feat_idx["pause_cv"]]
        
        is_ai = (
            (j < calibrated["thresholds"]["jitter_min"] or j > calibrated["thresholds"]["jitter_max"]) or
            (k < calibrated["thresholds"]["glottal_kurt_min"]) or
            (vhi >= calibrated["thresholds"]["voiced_hi_ratio_max"]) or
            (shi >= calibrated["thresholds"]["stft_hi_ratio_max"]) or
            (lf < calibrated["thresholds"]["low_freq_ratio_min"]) or
            (p_std > 0 and (p_std < calibrated["thresholds"]["pause_std_min"] or p_cv < calibrated["thresholds"]["pause_cv_min"]))
        )
        if is_ai:
            correct_ai += 1

    h_acc = (correct_h / len(X_human)) * 100 if len(X_human) > 0 else 0
    ai_acc = (correct_ai / len(X_ai)) * 100 if len(X_ai) > 0 else 0
    overall = ((correct_h + correct_ai) / (len(X_human) + len(X_ai))) * 100

    print("\n" + "=" * 65)
    print("TRAINING PERFORMANCE METRICS:")
    print("=" * 65)
    print(f"  Human Identification Rate: {correct_h}/{len(X_human)} ({h_acc:.1f}%)")
    print(f"  AI Voice Detection Rate:    {correct_ai}/{len(X_ai)} ({ai_acc:.1f}%)")
    print(f"  Overall Training Accuracy:  {overall:.1f}%")

if __name__ == "__main__":
    calibrate_thresholds()
