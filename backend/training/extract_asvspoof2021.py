import os
import sys
import time
import urllib.request
import pyarrow.parquet as pq

BASE_DIR = r"c:\Users\mahesh\Desktop\VoxGuard"
DATA_DIR = os.path.join(BASE_DIR, "training_data")
HUMAN_DIR = os.path.join(DATA_DIR, "human_bonafide")
ASVSPOOF_DIR = os.path.join(DATA_DIR, "asvspoof")

os.makedirs(HUMAN_DIR, exist_ok=True)
os.makedirs(ASVSPOOF_DIR, exist_ok=True)

def extract_parquet(parquet_path: str, tag: str, max_spoof: int = 5000):
    if not os.path.exists(parquet_path):
        print(f"[SKIP] File not found: {parquet_path}")
        return 0, 0
        
    print(f"\n[EXTRACT] Reading {parquet_path} ({tag})...")
    table = pq.read_table(parquet_path)
    pyd = table.to_pydict()
    print(f"  Loaded {len(table):,} rows. Columns: {table.column_names}")
    
    paths = pyd['path']
    audios = pyd['audio']
    labels = pyd['label']
    
    extracted_human = 0
    extracted_spoof = 0
    
    for i in range(len(table)):
        lbl = int(labels[i])
        fname = paths[i]
        stem = os.path.splitext(os.path.basename(fname))[0]
        
        if lbl == 0:
            out_path = os.path.join(HUMAN_DIR, f"{tag}_bona_{stem}.flac")
            if not os.path.exists(out_path):
                b = audios[i].get('bytes') if isinstance(audios[i], dict) else None
                if b:
                    with open(out_path, "wb") as f:
                        f.write(b)
            extracted_human += 1
        elif lbl == 1 and extracted_spoof < max_spoof:
            out_path = os.path.join(ASVSPOOF_DIR, f"{tag}_spoof_{stem}.flac")
            if not os.path.exists(out_path):
                b = audios[i].get('bytes') if isinstance(audios[i], dict) else None
                if b:
                    with open(out_path, "wb") as f:
                        f.write(b)
            extracted_spoof += 1
            
        if (i + 1) % 2000 == 0 or (i + 1) == len(table):
            print(f"  Processed {i+1}/{len(table)} -> {extracted_human} bona fide, {extracted_spoof} spoof attacks...", flush=True)
            
    print(f"[DONE] {tag}: {extracted_human} bona fide humans, {extracted_spoof} spoof attacks extracted!")
    return extracted_human, extracted_spoof

def download_file(url: str, dst_path: str, desc: str):
    if os.path.exists(dst_path) and os.path.getsize(dst_path) > 10 * 1024 * 1024:
        print(f"[EXISTS] {desc} already exists ({os.path.getsize(dst_path)/(1024*1024):.1f} MB), skipping download.")
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

def main():
    print("=" * 75)
    print("VOXGUARD ASVSPOOF 2021 PIPELINE: DOWNLOAD & EXTRACTION")
    print("=" * 75)
    
    # 1. Extract Shard 0 (already downloaded)
    shard0_path = os.path.join(DATA_DIR, "asvspoof2021_la_test_00000.parquet")
    extract_parquet(shard0_path, tag="asv21_la_s0", max_spoof=6000)
    
    # 2. Download and Extract Shard 1
    shard1_url = "https://huggingface.co/datasets/SpeechAntiSpoofingBenchmarks/ASVspoof2021_LA/resolve/main/data/test-00001-of-00024.parquet"
    shard1_dst = os.path.join(DATA_DIR, "asvspoof2021_la_test_00001.parquet")
    if download_file(shard1_url, shard1_dst, "ASVspoof 2021 LA Shard 1 (300 MB)"):
        extract_parquet(shard1_dst, tag="asv21_la_s1", max_spoof=6000)
        
    print("\n[ASVSPOOF 2021 DATASETS EXTRACTED SUCCESSFULLY!]")

if __name__ == "__main__":
    main()
