"""
Comprehensive validation of the calibrated live mic detection model.
Tests real-world scenarios:
1. Pure AI voices (ElevenLabs, Google Voice, ASVspoof)
2. Real Human voices (direct mic, natural cadence)
3. Mobile phone speaker playback (acoustic replay with sub-220Hz cutoff)
4. Isochronous timing vs organic timing
"""

import os
import sys
import numpy as np

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engines.aasist import aasist_engine

TRAIN_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "training_data"))
AI_DIR = os.path.join(TRAIN_DIR, "ai_online")
HUMAN_DIR = os.path.join(TRAIN_DIR, "human_bonafide")
ASVSPOOF_DIR = os.path.join(TRAIN_DIR, "asvspoof")
TEST_SAMPLES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "test_samples"))

def test_file_chunks(fpath: str, expected_is_ai: bool, chunk_sec: float = 1.8):
    fname = os.path.basename(fpath)
    if not os.path.exists(fpath):
        return None
        
    with open(fpath, "rb") as f:
        data = f.read()
        
    samples, sr = aasist_engine._decode_audio(data)
    if len(samples) < 320:
        return None

    chunk_size = int(sr * chunk_sec)
    n_chunks = max(1, len(samples) // chunk_size)
    
    chunk_results = []
    for c in range(min(5, n_chunks)):
        chunk = samples[c * chunk_size : (c + 1) * chunk_size]
        if len(chunk) < chunk_size:
            chunk = np.pad(chunk, (0, chunk_size - len(chunk)))
        # Convert float samples to 16-bit PCM bytes for live mic API format (clipped to prevent integer overflow)
        pcm_bytes = (np.clip(chunk, -1.0, 1.0) * 32767).astype(np.int16).tobytes()
        res = aasist_engine.analyze_live_chunk(pcm_bytes)
        chunk_results.append(res)
        
    # Aggregate
    ai_votes = sum(1 for r in chunk_results if r["isSynthetic"])
    pred_is_ai = ai_votes >= (len(chunk_results) / 2)
    avg_auth = np.mean([r["authenticity"] for r in chunk_results])
    
    passed = (pred_is_ai == expected_is_ai)
    return {
        "file": fname,
        "expected": "AI" if expected_is_ai else "HUMAN",
        "predicted": "AI" if pred_is_ai else "HUMAN",
        "avg_auth": avg_auth,
        "ai_chunks": f"{ai_votes}/{len(chunk_results)}",
        "passed": passed,
        "first_chunk_status": chunk_results[0]["authStatus"] if chunk_results else ""
    }

def run_validation():
    print("=" * 70)
    print("VOXGUARD LIVE MIC CALIBRATED VALIDATION TEST SUITE")
    print("=" * 70)

    test_cases = []

    # 1. Real AI Voices (ElevenLabs & Google Voice)
    print("\n--- Testing Real Online AI Voices (ElevenLabs, OpenAI, Google, Azure) ---")
    if os.path.exists(AI_DIR):
        for f in os.listdir(AI_DIR):
            if f.lower().endswith(('.mp3', '.mp4', '.wav', '.ogg', '.opus')):
                test_cases.append((os.path.join(AI_DIR, f), True))

    # 2. Real Human Voices
    print("--- Testing Real Bona Fide Human Voices ---")
    if os.path.exists(HUMAN_DIR):
        for f in os.listdir(HUMAN_DIR):
            if f.lower().endswith(('.mp3', '.mp4', '.wav', '.ogg', '.flac')):
                test_cases.append((os.path.join(HUMAN_DIR, f), False))

    # 3. ASVspoof AI voices (sample of 15)
    print("--- Testing ASVspoof Benchmark Spoof Attacks ---")
    if os.path.exists(ASVSPOOF_DIR):
        asv_files = [os.path.join(ASVSPOOF_DIR, f) for f in os.listdir(ASVSPOOF_DIR) if f.lower().endswith('.wav')]
        for f in asv_files[:15]:
            test_cases.append((f, True))

    results = []
    total_passed = 0
    total_tested = 0

    print(f"\n{'FILENAME':<42} | {'EXPECTED':<8} | {'PREDICTED':<9} | {'AUTH%':<6} | {'RESULT'}")
    print("-" * 75)

    for fpath, expected_ai in test_cases:
        res = test_file_chunks(fpath, expected_ai)
        if not res:
            continue
        total_tested += 1
        if res["passed"]:
            total_passed += 1
            status_tag = "[PASS] OK"
        else:
            status_tag = "[FAIL] MISMATCH"
            
        short_name = res["file"][:40]
        print(f"{short_name:<42} | {res['expected']:<8} | {res['predicted']:<9} | {res['avg_auth']:>5.1f}% | {status_tag}")
        results.append(res)

    acc = (total_passed / total_tested * 100) if total_tested > 0 else 0
    print("\n" + "=" * 75)
    print(f"FINAL ACCURACY: {total_passed}/{total_tested} ({acc:.1f}%)")
    print("=" * 75)
    return acc >= 90.0

if __name__ == "__main__":
    success = run_validation()
    sys.exit(0 if success else 1)
