import os
import sys
import requests
import pyarrow.parquet as pq
import io
import soundfile as sf
import numpy as np

TRAIN_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "training_data"))
HUMAN_DIR = os.path.join(TRAIN_DIR, "human_bonafide")
os.makedirs(HUMAN_DIR, exist_ok=True)

MINDS14_URL = "https://huggingface.co/datasets/PolyAI/minds14/resolve/main/en-US/train-00000-of-00001.parquet"
DEST_PARQUET = os.path.join(TRAIN_DIR, "minds14_en_us.parquet")

def download_minds14():
    print("=" * 70)
    print("DOWNLOADING RICH MULTI-SPEAKER HUMAN DATASET (PolyAI Minds14 en-US)")
    print("=" * 70)
    
    if not os.path.exists(DEST_PARQUET) or os.path.getsize(DEST_PARQUET) < 30000000:
        print(f"Downloading from {MINDS14_URL} (~34 MB)...")
        r = requests.get(MINDS14_URL, stream=True, timeout=60)
        r.raise_for_status()
        with open(DEST_PARQUET, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)
        print(f"[DOWNLOADED] Saved to: {DEST_PARQUET} ({os.path.getsize(DEST_PARQUET):,} bytes)")
    else:
        print(f"[FOUND] Existing dataset at: {DEST_PARQUET}")

    # Extract human WAV files
    print("\nExtracting genuine human speech samples...")
    table = pq.read_table(DEST_PARQUET)
    data = table.to_pydict()
    audios = data.get("audio", [])
    print(f"Total human recordings in dataset: {len(audios)}")
    
    extracted = 0
    for idx, item in enumerate(audios):
        dest_wav = os.path.join(HUMAN_DIR, f"minds14_human_{idx}.wav")
        if os.path.exists(dest_wav) and os.path.getsize(dest_wav) > 1000:
            extracted += 1
            continue
            
        audio_bytes = None
        if isinstance(item, dict):
            audio_bytes = item.get("bytes")
        elif isinstance(item, bytes):
            audio_bytes = item
            
        if audio_bytes and len(audio_bytes) > 500:
            with open(dest_wav, "wb") as f:
                f.write(audio_bytes)
            extracted += 1
            if extracted % 50 == 0:
                print(f"  Extracted {extracted}/{len(audios)} human voice files...")
                
    print(f"\n[COMPLETE] Successfully extracted {extracted} bona fide human voice files into: {HUMAN_DIR}")

if __name__ == "__main__":
    download_minds14()
