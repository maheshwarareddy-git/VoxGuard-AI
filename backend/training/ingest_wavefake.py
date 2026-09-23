import os
import sys
import time
import urllib.request
import pyarrow.parquet as pq

BASE_DIR = r"c:\Users\mahesh\Desktop\VoxGuard"
DATA_DIR = os.path.join(BASE_DIR, "training_data")
ASVSPOOF_DIR = os.path.join(DATA_DIR, "asvspoof")
os.makedirs(ASVSPOOF_DIR, exist_ok=True)

PARQUET_URL = "https://huggingface.co/datasets/ajaykarthick/wavefake-audio/resolve/main/data/partition0-00000-of-00001.parquet"
PARQUET_FILE = os.path.join(DATA_DIR, "wavefake_partition0.parquet")

def download_file(url: str, dst_path: str, desc: str):
    if os.path.exists(dst_path) and os.path.getsize(dst_path) > 10 * 1024 * 1024:
        print(f"[EXISTS] {desc} ({os.path.getsize(dst_path)/(1024*1024):.1f} MB) already exists, skipping download.")
        return True
    tmp_path = dst_path + ".tmp"
    print(f"\n[DOWNLOAD] Starting download of {desc}...")
    t0 = time.time()
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            total_sz = int(resp.headers.get('Content-Length', 0))
            downloaded = 0
            with open(tmp_path, "wb") as f:
                while True:
                    chunk = resp.read(1024 * 1024 * 4)
                    if not chunk: break
                    f.write(chunk)
                    downloaded += len(chunk)
                    el = time.time() - t0
                    speed = (downloaded / (1024*1024)) / (el + 1e-6)
                    pct = (downloaded / total_sz) * 100 if total_sz else 0
                    if int(el) % 5 == 0 or downloaded == total_sz:
                        print(f"  {downloaded/(1024*1024):.1f}/{total_sz/(1024*1024):.1f} MB ({pct:.1f}%) at {speed:.2f} MB/s", flush=True)
        if os.path.exists(dst_path): os.remove(dst_path)
        os.rename(tmp_path, dst_path)
        print(f"[COMPLETE] {desc} downloaded in {time.time()-t0:.1f}s -> {dst_path}")
        return True
    except Exception as e:
        print(f"[ERROR] Failed downloading {desc}: {e}")
        if os.path.exists(tmp_path):
            try: os.remove(tmp_path)
            except: pass
        return False

def extract_wavefake(parquet_path: str, max_extract: int = 2500):
    if not os.path.exists(parquet_path):
        return 0
    print(f"\n[EXTRACT] Reading WaveFake parquet {parquet_path}...")
    table = pq.read_table(parquet_path)
    pyd = table.to_pydict()
    print("  Columns in WaveFake dataset:", list(pyd.keys()))
    
    audios = pyd.get('audio', [])
    labels = pyd.get('label', pyd.get('fake', []))
    files = pyd.get('file', pyd.get('path', pyd.get('id', [])))
    
    extracted = 0
    for i in range(len(table)):
        if extracted >= max_extract:
            break
        
        # Audio bytes
        b = None
        if i < len(audios) and isinstance(audios[i], dict):
            b = audios[i].get('bytes')
        if not b:
            continue

        fname = files[i] if i < len(files) else f"wavefake_{i}"
        stem = os.path.splitext(os.path.basename(str(fname)))[0]
        out_path = os.path.join(ASVSPOOF_DIR, f"wavefake_spoof_{stem}_{i}.wav")
        if not os.path.exists(out_path):
            with open(out_path, "wb") as f:
                f.write(b)
        extracted += 1

        if (extracted % 500 == 0) or extracted == max_extract:
            print(f"  Extracted {extracted}/{max_extract} WaveFake neural vocoder samples...", flush=True)

    print(f"[DONE] Extracted {extracted} WaveFake samples to {ASVSPOOF_DIR}.")
    return extracted

def main():
    print("=" * 75)
    print("VOXGUARD WAVEFAKE DATASET INGESTION (MELGAN, HIFIGAN, PWG, WAVEGLOW)")
    print("=" * 75)
    if download_file(PARQUET_URL, PARQUET_FILE, "WaveFake Partition 0 (222 MB)"):
        extract_wavefake(PARQUET_FILE, max_extract=2500)

if __name__ == "__main__":
    main()
