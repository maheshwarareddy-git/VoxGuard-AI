"""
Train a machine learning classifier (RandomForest + Multi-Platform Biophysical Ensemble)
on real audio chunks from OpenAI, Google/Gemini, ElevenLabs, Azure/Copilot, ASVspoof, and real humans.
Saves the trained model to backend/engines/trained_live_classifier.joblib.
"""

import os
import sys
import json
import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.metrics import classification_report, confusion_matrix

sys.stdout.reconfigure(encoding='utf-8')

TRAIN_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "training_data"))
FEATURES_FILE = os.path.join(TRAIN_DIR, "extracted_features.npz")
MODEL_OUTPUT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "engines", "trained_live_classifier.joblib"))
CONFIG_OUTPUT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "engines", "trained_model_config.json"))

def train_and_save_model():
    print("=" * 70)
    print("VOXGUARD MULTI-PLATFORM AI VOICE MODEL TRAINING")
    print("=" * 70)

    if not os.path.exists(FEATURES_FILE):
        print(f"[ERROR] Features file {FEATURES_FILE} not found!")
        sys.exit(1)

    data = np.load(FEATURES_FILE, allow_pickle=True)
    X = data["X"]
    y = data["y"]
    feature_names = list(data["feature_names"])
    sources = list(data["sources"])

    print(f"[DATASET OVERVIEW] Total Chunks: {len(y)}")
    print(f"  Human Bonafide (0): {sum(y == 0)}")
    print(f"  AI Synthetic (1):   {sum(y == 1)}")
    print(f"  Feature Count:      {len(feature_names)}")

    # Classify sources by AI platform
    platforms = {
        "Human (Bona Fide)": [i for i, s in enumerate(sources) if y[i] == 0],
        "OpenAI (ChatGPT / GPT-4o)": [i for i, s in enumerate(sources) if y[i] == 1 and "openai" in s.lower()],
        "Google & Gemini Voice": [i for i, s in enumerate(sources) if y[i] == 1 and ("google" in s.lower() or "gtts" in s.lower())],
        "Azure / Copilot / Neural TTS": [i for i, s in enumerate(sources) if y[i] == 1 and "neural" in s.lower()],
        "ElevenLabs Voices": [i for i, s in enumerate(sources) if y[i] == 1 and "elevenlabs" in s.lower()],
        "ASVspoof Challenge Audio": [i for i, s in enumerate(sources) if y[i] == 1 and "asvspoof" in s.lower()],
    }

    print("\n[CHUNKS PER PLATFORM]")
    for p_name, p_idx in platforms.items():
        print(f"  {p_name:<30}: {len(p_idx)} chunks")

    # Stratified 5-Fold Cross Validation
    clf = RandomForestClassifier(
        n_estimators=180,
        max_depth=9,
        min_samples_split=4,
        class_weight="balanced",
        random_state=42
    )

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    scores = cross_val_score(clf, X, y, cv=cv, scoring="accuracy")
    print(f"\n[CROSS-VALIDATION 5-FOLD] Mean Accuracy: {np.mean(scores)*100:.2f}% ± {np.std(scores)*100:.2f}%")

    # Fit on all data
    clf.fit(X, y)

    # Predictions & probabilities
    probs = clf.predict_proba(X)[:, 1]
    preds = (probs >= 0.5).astype(int)

    cm = confusion_matrix(y, preds)
    print("\n[CONFUSION MATRIX]")
    print(f"  True Human: {cm[0, 0]} correctly detected, {cm[0, 1]} false alarms")
    print(f"  True AI:    {cm[1, 1]} correctly detected, {cm[1, 0]} missed")

    # Per-Platform Detection Performance
    print("\n" + "=" * 70)
    print("PER-PLATFORM LIVE DETECTION ACCURACY:")
    print("=" * 70)
    for p_name, indices in platforms.items():
        if not indices:
            continue
        if "Human" in p_name:
            correct = sum(preds[i] == 0 for i in indices)
            acc = (correct / len(indices)) * 100
            print(f"  {p_name:<32}: {correct}/{len(indices)} verified ({acc:.1f}%)")
        else:
            correct = sum(preds[i] == 1 for i in indices)
            acc = (correct / len(indices)) * 100
            print(f"  {p_name:<32}: {correct}/{len(indices)} detected ({acc:.1f}%)")

    # Feature Importance
    importances = clf.feature_importances_
    sorted_idx = np.argsort(importances)[::-1]
    print("\n[FEATURE IMPORTANCE RANKING]")
    for rank, idx in enumerate(sorted_idx, 1):
        print(f"  {rank:2d}. {feature_names[idx]:<20}: {importances[idx]*100:.2f}%")

    # Save trained model
    joblib.dump({
        "model": clf,
        "feature_names": feature_names,
        "classes": [0, 1]
    }, MODEL_OUTPUT)
    print(f"\n[SAVED] Trained model saved to: {MODEL_OUTPUT}")

    # Save configuration and stats
    config = {
        "model_type": "MultiPlatformRandomForestClassifier",
        "training_samples": int(len(y)),
        "human_samples": int(sum(y == 0)),
        "ai_samples": int(sum(y == 1)),
        "cv_mean_accuracy": float(round(np.mean(scores) * 100, 2)),
        "platforms_trained": list(platforms.keys()),
        "feature_names": feature_names,
        "feature_importances": {feature_names[i]: float(round(importances[i] * 100, 2)) for i in sorted_idx}
    }
    with open(CONFIG_OUTPUT, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)
    print(f"[SAVED] Model config saved to: {CONFIG_OUTPUT}")

if __name__ == "__main__":
    train_and_save_model()
