"""
Extract DSP and acoustic features from training audio chunks (1.8s slices).
Matches the exact signal processing pipeline of AASISTAuthenticityEngine.analyze_live_chunk.
"""

import os
import sys
import numpy as np
import scipy.signal as signal
from scipy.stats import kurtosis
from typing import List, Dict, Any

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from engines.aasist import AASISTAuthenticityEngine

sys.stdout.reconfigure(encoding='utf-8')

TRAIN_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "training_data"))
ASVSPOOF_DIR = os.path.join(TRAIN_DIR, "asvspoof")
AI_DIR = os.path.join(TRAIN_DIR, "ai_online")
HUMAN_DIR = os.path.join(TRAIN_DIR, "human_bonafide")
OUTPUT_FEATURES = os.path.join(TRAIN_DIR, "extracted_features.npz")

engine = AASISTAuthenticityEngine()

def extract_chunk_features(samples: np.ndarray, sr: int = 16000) -> Dict[str, float]:
    """Extracts the exact 10 acoustic & cadence features from a 1.8s audio chunk."""
    if len(samples) < 320:
        return None

    rms_energy = float(np.sqrt(np.mean(samples ** 2)))
    peak_amp = float(np.max(np.abs(samples)))
    if peak_amp < 0.025 or rms_energy < 0.005:
        return None  # Silence / ambient background

    norm_samples = samples - np.mean(samples)
    max_val = np.max(np.abs(norm_samples))
    if max_val > 1e-6:
        norm_samples = norm_samples / max_val

    zcr = float(np.mean(np.abs(np.diff(np.sign(norm_samples))))) / 2.0

    frame_len = int(sr * 0.030)
    hop_len = int(sr * 0.015)
    num_frames = (len(norm_samples) - frame_len) // hop_len
    min_lag = max(2, int(sr / 450))
    max_lag = min(frame_len - 1, int(sr / 70))

    voiced_f0: List[float] = []
    voiced_hi_ratios: List[float] = []
    frame_energies: List[float] = []

    for i in range(num_frames):
        frame = norm_samples[i * hop_len : i * hop_len + frame_len]
        energy = float(np.sqrt(np.mean(frame ** 2)))
        frame_energies.append(energy)
        if energy < 0.018:
            continue

        corr = np.correlate(frame, frame, mode='full')[frame_len - 1 :]
        if len(corr) <= max_lag:
            continue
        window = corr[min_lag:max_lag]
        if len(window) == 0:
            continue
        peak_idx = int(np.argmax(window)) + min_lag
        periodicity = corr[peak_idx] / (corr[0] + 1e-12)

        if periodicity > 0.42:
            voiced_f0.append(sr / peak_idx)
            fft_mag = np.abs(np.fft.rfft(frame * np.hamming(frame_len)))
            freqs = np.fft.rfftfreq(frame_len, 1 / sr)
            hi_e = np.mean(fft_mag[freqs >= 6500])
            mid_e = np.mean(fft_mag[(freqs >= 1500) & (freqs <= 3500)])
            if mid_e > 0.020:
                voiced_hi_ratios.append(float(hi_e / mid_e))

    if len(voiced_f0) < 4:
        return None  # Insufficient voiced speech frames

    mean_f0 = float(np.mean(voiced_f0))
    std_f0 = float(np.std(voiced_f0))
    pitch_cv = (std_f0 / (mean_f0 + 1e-6)) * 100.0
    pitch_range = float(np.max(voiced_f0) - np.min(voiced_f0))

    local_jitters: List[float] = []
    for k in range(1, len(voiced_f0)):
        diff_ratio = abs(voiced_f0[k] - voiced_f0[k - 1]) / (voiced_f0[k - 1] + 1e-6)
        if diff_ratio < 0.20:
            local_jitters.append(diff_ratio * 100.0)
    jitter = float(np.mean(local_jitters)) if local_jitters else 0.85

    # Speech Cadence & Pause Statistics
    avg_energy = float(np.mean(frame_energies))
    is_speech = np.array(frame_energies) > (avg_energy * 0.35)
    pauses: List[float] = []
    curr_pause = 0
    for s in is_speech:
        if not s:
            curr_pause += 1
        else:
            if curr_pause >= 2:
                pauses.append(curr_pause * 0.015)
            curr_pause = 0

    pause_std = float(np.std(pauses)) if len(pauses) >= 2 else 0.0
    pause_mean = float(np.mean(pauses)) if pauses else 0.0
    pause_cv = (pause_std / (pause_mean + 1e-6)) if pauses else 0.0

    voiced_hi_ratio = float(np.mean(voiced_hi_ratios)) if voiced_hi_ratios else 0.10

    try:
        analytic_signal = signal.hilbert(norm_samples[: min(len(norm_samples), 65536)])
        amplitude_envelope = np.abs(analytic_signal)
        env_diff_kurt = float(kurtosis(np.diff(amplitude_envelope)))
    except Exception:
        env_diff_kurt = 15.0

    full_fft = np.abs(np.fft.rfft(norm_samples[: min(len(norm_samples), 32768)]))
    full_psd = (full_fft ** 2) + 1e-12
    full_psd_prob = full_psd / np.sum(full_psd)
    spectral_entropy = -float(np.sum(full_psd_prob * np.log2(full_psd_prob + 1e-12))) / 10.0
    spectral_entropy = float(np.clip(spectral_entropy, 0.05, 1.0))

    f_stft, t_stft, Zxx = signal.stft(norm_samples, fs=sr, nperseg=512, noverlap=256)
    stft_mag = np.abs(Zxx)
    stft_hi_band = float(np.mean(stft_mag[f_stft >= 7000, :]))
    stft_mid_band = float(np.mean(stft_mag[(f_stft >= 2000) & (f_stft <= 4000), :]))
    stft_hi_ratio = float(stft_hi_band / (stft_mid_band + 1e-12))

    full_f_lc = np.fft.rfftfreq(min(len(norm_samples), 32768), 1 / sr)
    low_e = float(np.sum(full_fft[full_f_lc < 220] ** 2))
    mid_e = float(np.sum(full_fft[(full_f_lc >= 500) & (full_f_lc <= 2500)] ** 2))
    low_freq_ratio = float(low_e / (mid_e + 1e-12))

    return {
        "jitter": jitter,
        "pitch_cv": pitch_cv,
        "pitch_range": pitch_range,
        "voiced_hi_ratio": voiced_hi_ratio,
        "stft_hi_ratio": stft_hi_ratio,
        "env_diff_kurt": env_diff_kurt,
        "low_freq_ratio": low_freq_ratio,
        "pause_std": pause_std,
        "pause_cv": pause_cv,
        "pause_mean": pause_mean,
        "spectral_entropy": spectral_entropy,
        "zcr": zcr,
        "voiced_frames": len(voiced_f0),
        "num_pauses": len(pauses)
    }

def process_directory(dir_path: str, label: int, chunk_sec: float = 1.8) -> List[Dict[str, Any]]:
    """Reads all audio in dir, splits into chunk_sec slices, and extracts features."""
    results = []
    if not os.path.exists(dir_path):
        return results

    files = [os.path.join(dir_path, f) for f in os.listdir(dir_path) if f.lower().endswith(('.wav', '.mp3', '.mp4', '.ogg', '.flac', '.opus'))]
    print(f"[PROCESSING] {len(files)} files in {os.path.basename(dir_path)} (label={label})...")

    chunk_samples = int(16000 * chunk_sec)
    hop_samples = int(chunk_samples * 0.75)  # 25% overlap for continuous coverage

    for fpath in files:
        fname = os.path.basename(fpath)
        try:
            with open(fpath, "rb") as f:
                raw_bytes = f.read()
            samples, sr = engine._decode_audio(raw_bytes)
            if len(samples) < chunk_samples:
                feat = extract_chunk_features(samples, sr)
                if feat:
                    feat["label"] = label
                    feat["source_file"] = fname
                    results.append(feat)
            else:
                n_chunks = 0
                for start in range(0, len(samples) - chunk_samples + 1, hop_samples):
                    chunk = samples[start : start + chunk_samples]
                    feat = extract_chunk_features(chunk, sr)
                    if feat:
                        feat["label"] = label
                        feat["source_file"] = f"{fname}_c{n_chunks}"
                        results.append(feat)
                        n_chunks += 1
        except Exception as e:
            print(f"  Error on {fname}: {e}")

    print(f"  Extracted {len(results)} valid speech chunks from {os.path.basename(dir_path)}.")
    return results

if __name__ == "__main__":
    print("=" * 60)
    print("VOXGUARD FEATURE EXTRACTION ON REAL AUDIO CHUNKS")
    print("=" * 60)

    # Label: 0 = Bonafide Human, 1 = AI Spoof
    human_chunks = process_directory(HUMAN_DIR, label=0)
    asvspoof_chunks = process_directory(ASVSPOOF_DIR, label=1)
    ai_online_chunks = process_directory(AI_DIR, label=1)

    all_chunks = human_chunks + asvspoof_chunks + ai_online_chunks
    print(f"\n[SUMMARY] Total extracted valid chunks: {len(all_chunks)}")
    print(f"  Human Bonafide: {len(human_chunks)}")
    print(f"  ASVspoof AI: {len(asvspoof_chunks)}")
    print(f"  Online AI (ElevenLabs, GV): {len(ai_online_chunks)}")

    if not all_chunks:
        print("[ERROR] No chunks extracted. Check dataset folders.")
        sys.exit(1)

    feature_keys = [
        "jitter", "pitch_cv", "pitch_range", "voiced_hi_ratio", "stft_hi_ratio",
        "env_diff_kurt", "low_freq_ratio", "pause_std", "pause_cv", "pause_mean",
        "spectral_entropy", "zcr"
    ]

    X = np.array([[chunk[k] for k in feature_keys] for chunk in all_chunks], dtype=np.float32)
    y = np.array([chunk["label"] for chunk in all_chunks], dtype=np.int32)
    sources = [chunk["source_file"] for chunk in all_chunks]

    np.savez(
        OUTPUT_FEATURES,
        X=X,
        y=y,
        feature_names=feature_keys,
        sources=sources
    )
    print(f"[SAVED] Feature dataset written to: {OUTPUT_FEATURES}")
    print(f"  Matrix shape: {X.shape}, Labels shape: {y.shape}")
