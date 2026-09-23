import os
import sys
import time
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_DIR = r"c:\Users\mahesh\Desktop\VoxGuard"
BACKEND_DIR = os.path.join(BASE_DIR, "backend")
TRAIN_DIR = os.path.join(BASE_DIR, "training_data")
HUMAN_DIR = os.path.join(TRAIN_DIR, "human_bonafide")
AI_DIR = os.path.join(TRAIN_DIR, "ai_online")
ASVSPOOF_DIR = os.path.join(TRAIN_DIR, "asvspoof")
FEATURES_FILE = os.path.join(TRAIN_DIR, "extracted_features_megascale.npz")

sys.path.insert(0, BACKEND_DIR)
from training.train_megascale_master import extract_chunk_features, process_single_file

def main():
    print("=" * 75)
    print("VOXGUARD HIGH-THROUGHPUT INCREMENTAL FEATURE EXTRACTOR")
    print("=" * 75)
    t0 = time.time()

    # 1. Load existing cache
    existing_chunks = []
    cached_file_stems = set()
    feature_keys = [
        "jitter", "pitch_cv", "pitch_range", "voiced_hi_ratio", "stft_hi_ratio",
        "env_diff_kurt", "low_freq_ratio", "pause_std", "pause_cv", "pause_mean",
        "spectral_entropy", "zcr"
    ]

    if os.path.exists(FEATURES_FILE):
        print(f"Loading existing feature cache from {FEATURES_FILE}...")
        cdata = np.load(FEATURES_FILE)
        old_X = cdata["X"]
        old_y = cdata["y"]
        old_sources = list(cdata["sources"])
        print(f"  Loaded {len(old_X):,} existing chunks.")
        
        for i in range(len(old_X)):
            s = old_sources[i]
            row_dict = dict(zip(feature_keys, old_X[i]))
            row_dict["label"] = int(old_y[i])
            row_dict["source"] = s
            existing_chunks.append(row_dict)
            
            # Record stem
            stem = s.split("_c")[0] if "_c" in s else s
            stem = os.path.splitext(stem)[0]
            cached_file_stems.add(stem.lower())
            
        print(f"  Existing chunks map to {len(cached_file_stems):,} unique audio file stems.")

    # 2. Identify new files
    def get_new_files(dir_path):
        if not os.path.exists(dir_path): return []
        all_f = [os.path.join(dir_path, f) for f in os.listdir(dir_path) if f.lower().endswith(('.wav', '.mp3', '.m4a', '.flac', '.ogg'))]
        new_f = []
        for f in all_f:
            stem = os.path.splitext(os.path.basename(f))[0].lower()
            if stem not in cached_file_stems:
                new_f.append(f)
        return new_f

    new_human = get_new_files(HUMAN_DIR)
    new_asv = get_new_files(ASVSPOOF_DIR)
    new_ai = get_new_files(AI_DIR)

    print(f"\n[NEW FILES REQUIRING EXTRACTION]")
    print(f"  New Bona Fide Human Files: {len(new_human):,}")
    print(f"  New ASVspoof Attack Files: {len(new_asv):,}")
    print(f"  New AI Online Files:       {len(new_ai):,}")
    total_new = len(new_human) + len(new_asv) + len(new_ai)
    print(f"  Total New Files to Extract: {total_new:,}")

    if total_new == 0:
        print("No new files found to extract. Cache is 100% up-to-date!")
        return

    # 3. Parallel extraction of new files
    def extract_batch(files, label, desc):
        if not files: return []
        print(f"\nExtracting {len(files):,} files from {desc} using 16 threads...")
        chunks = []
        done = 0
        with ThreadPoolExecutor(max_workers=16) as executor:
            futures = {executor.submit(process_single_file, f, label): f for f in files}
            for fut in as_completed(futures):
                res = fut.result()
                if res:
                    chunks.extend(res)
                done += 1
                if done % 1000 == 0 or done == len(files):
                    print(f"  {done}/{len(files)} files processed -> {len(chunks):,} chunks extracted", flush=True)
        return chunks

    new_human_chunks = extract_batch(new_human, label=0, desc="Human Bona Fide (Fleurs Indic + ASVspoof S1)")
    new_asv_chunks = extract_batch(new_asv, label=1, desc="ASVspoof Challenge Attacks (Shard 0 & 1)")
    new_ai_chunks = extract_batch(new_ai, label=1, desc="AI Online Voices")

    # 4. Merge
    all_chunks = existing_chunks + new_human_chunks + new_asv_chunks + new_ai_chunks
    print(f"\n[FINAL MEGASCALE DATASET SUMMARY]")
    total_human = sum(1 for c in all_chunks if c["label"] == 0)
    total_ai = sum(1 for c in all_chunks if c["label"] == 1)
    print(f"  Bona Fide Human Chunks: {total_human:,}")
    print(f"  AI Spoof & Clones:      {total_ai:,}")
    print(f"  Total Training Chunks:  {len(all_chunks):,}")

    X = np.array([[c[k] for k in feature_keys] for c in all_chunks], dtype=np.float32)
    y = np.array([c["label"] for c in all_chunks], dtype=np.int32)
    sources = [c["source"] for c in all_chunks]

    np.savez(FEATURES_FILE, X=X, y=y, feature_names=feature_keys, sources=sources)
    print(f"\n[SAVED] Updated Megascale feature matrix saved to: {FEATURES_FILE}")
    print(f"  Matrix shape: {X.shape}, Elapsed: {time.time() - t0:.1f}s")

if __name__ == "__main__":
    main()
