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
                    chunk = resp.read(1024 * 1024 * 4) # 4MB chunk
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    el = time.time() - t0
                    speed = (downloaded / (1024*1024)) / (el + 1e-6)
                    pct = (downloaded / total_sz) * 100 if total_sz else 0
                    if int(el) % 5 == 0 or downloaded == total_sz:
                        print(f"  {downloaded/(1024*1024):.1f}/{total_sz/(1024*1024):.1f} MB ({pct:.1f}%) at {speed:.2f} MB/s", flush=True)
        if os.path.exists(dst_path):
            os.remove(dst_path)
        os.rename(tmp_path, dst_path)
        print(f"[COMPLETE] {desc} downloaded in {time.time()-t0:.1f}s -> {dst_path}")
        return True
    except Exception as e:
        print(f"[ERROR] Failed downloading {desc}: {e}")
        if os.path.exists(tmp_path):
            try: os.remove(tmp_path)
            except: pass
        return False

def extract_fleurs_parquet(parquet_path: str, lang_tag: str):
    if not os.path.exists(parquet_path):
        return 0
    print(f"\n[EXTRACT FLEURS] Processing {parquet_path} ({lang_tag})...")
    table = pq.read_table(parquet_path)
    pyd = table.to_pydict()
    print(f"  Loaded {len(table):,} rows. Columns: {table.column_names}")
    
    audios = pyd.get('audio', [])
    ids = pyd.get('id', [f"fleurs_{lang_tag}_{i}" for i in range(len(table))])
    
    extracted = 0
    for i in range(len(table)):
        uid = ids[i]
        out_path = os.path.join(HUMAN_DIR, f"fleurs_{lang_tag}_{uid}.wav")
        if not os.path.exists(out_path):
            a_item = audios[i] if i < len(audios) else None
            b = a_item.get('bytes') if isinstance(a_item, dict) else None
            if b:
                with open(out_path, "wb") as f:
                    f.write(b)
                extracted += 1
        else:
            extracted += 1
            
        if (i + 1) % 200 == 0 or (i + 1) == len(table):
            print(f"  Extracted {extracted}/{len(table)} {lang_tag} human speech files...", flush=True)
            
    print(f"Extracted {extracted} genuine Indian human voice files for {lang_tag}!")
    return extracted

def extract_asvspoof_shard(parquet_path: str, shard_num: int):
    if not os.path.exists(parquet_path):
        return 0, 0
    print(f"\n[EXTRACT ASVSPOOF] Processing shard {shard_num}: {parquet_path}...")
    table = pq.read_table(parquet_path)
    pyd = table.to_pydict()
    print(f"  Loaded {len(table):,} rows. Columns: {table.column_names}")
    
    paths = pyd['path']
    audios = pyd['audio']
    labels = pyd['label']
    
    human_cnt = 0
    spoof_cnt = 0
    spoof_limit = 6000 # Extract up to 6000 attacks from this shard
    
    for i in range(len(table)):
        lbl = int(labels[i])
        fname = paths[i]
        stem = os.path.splitext(os.path.basename(fname))[0]
        
        if lbl == 0:
            out_path = os.path.join(HUMAN_DIR, f"asv19_s{shard_num}_bona_{stem}.flac")
            if not os.path.exists(out_path):
                b = audios[i].get('bytes') if isinstance(audios[i], dict) else None
                if b:
                    with open(out_path, "wb") as f:
                        f.write(b)
            human_cnt += 1
        elif lbl == 1 and spoof_cnt < spoof_limit:
            out_path = os.path.join(ASVSPOOF_DIR, f"asv19_s{shard_num}_spoof_{stem}.flac")
            if not os.path.exists(out_path):
                b = audios[i].get('bytes') if isinstance(audios[i], dict) else None
                if b:
                    with open(out_path, "wb") as f:
                        f.write(b)
            spoof_cnt += 1
            
        if (i + 1) % 1500 == 0 or (i + 1) == len(table):
            print(f"  Processed {i+1}/{len(table)} -> {human_cnt} bona fide, {spoof_cnt} attacks...", flush=True)
            
    print(f"Shard {shard_num} complete: {human_cnt} bona fide humans, {spoof_cnt} challenge attacks extracted!")
    return human_cnt, spoof_cnt

def main():
    print("=" * 75)
    print("VOXGUARD COLOSSAL DATASET EXPANSION: ASVSPOOF 2019 + INDIC FLEURS")
    print("=" * 75)
    
    # 1. Fleurs Hindi
    hi_url = "https://huggingface.co/datasets/google/fleurs/resolve/refs%2Fconvert%2Fparquet/hi_in/validation/0000.parquet"
    hi_dst = os.path.join(DATA_DIR, "fleurs_hi_in_val.parquet")
    if download_file(hi_url, hi_dst, "Fleurs Hindi Validation (154 MB)"):
        extract_fleurs_parquet(hi_dst, "hi")
        
    # 2. Fleurs Telugu
    te_url = "https://huggingface.co/datasets/google/fleurs/resolve/refs%2Fconvert%2Fparquet/te_in/validation/0000.parquet"
    te_dst = os.path.join(DATA_DIR, "fleurs_te_in_val.parquet")
    if download_file(te_url, te_dst, "Fleurs Telugu Validation (195 MB)"):
        extract_fleurs_parquet(te_dst, "te")
        
    # 3. ASVspoof 2019 Shard 1
    asv_s1_url = "https://huggingface.co/datasets/SpeechAntiSpoofingBenchmarks/ASVspoof2019_LA/resolve/refs%2Fconvert%2Fparquet/default/test/0001.parquet"
    asv_s1_dst = os.path.join(DATA_DIR, "asvspoof2019_test_0001.parquet")
    if download_file(asv_s1_url, asv_s1_dst, "ASVspoof 2019 LA Shard 1 (464 MB)"):
        extract_asvspoof_shard(asv_s1_dst, shard_num=1)
        
    print("\n[ALL DOWNLOADS & EXTRACTIONS COMPLETED SUCCESSFULLY!]")

if __name__ == "__main__":
    main()
