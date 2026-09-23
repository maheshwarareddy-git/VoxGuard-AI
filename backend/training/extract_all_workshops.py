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

def extract_string_label_parquet(parquet_path: str, tag: str):
    if not os.path.exists(parquet_path):
        print(f"[SKIP] Not found: {parquet_path}")
        return 0, 0
    print(f"\n[EXTRACT WORKSHOP] {parquet_path} ({tag})...")
    table = pq.read_table(parquet_path)
    pyd = table.to_pydict()
    files = pyd.get('file', pyd.get('path', []))
    audios = pyd['audio']
    labels = pyd['label']
    
    n_hum = 0
    n_spf = 0
    for i in range(len(table)):
        lbl_val = labels[i]
        is_human = False
        if isinstance(lbl_val, str):
            is_human = (lbl_val.lower() == 'authentic' or lbl_val.lower() == 'bonafide')
        elif isinstance(lbl_val, (int, float)):
            is_human = (int(lbl_val) == 0)
            
        fname = files[i] if i < len(files) else f"sample_{i}"
        stem = os.path.splitext(os.path.basename(fname))[0]
        
        b = audios[i].get('bytes') if isinstance(audios[i], dict) else None
        if not b:
            continue
            
        if is_human:
            out_path = os.path.join(HUMAN_DIR, f"{tag}_bona_{stem}.flac")
            if not os.path.exists(out_path):
                with open(out_path, "wb") as f: f.write(b)
            n_hum += 1
        else:
            out_path = os.path.join(ASVSPOOF_DIR, f"{tag}_spoof_{stem}.flac")
            if not os.path.exists(out_path):
                with open(out_path, "wb") as f: f.write(b)
            n_spf += 1
            
    print(f"[DONE] {tag}: {n_hum} bona fide humans, {n_spf} spoof attacks extracted.")
    return n_hum, n_spf

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

def extract_numeric_parquet(parquet_path: str, tag: str, max_spoof: int = 6000):
    if not os.path.exists(parquet_path): return 0, 0
    print(f"\n[EXTRACT] Reading {parquet_path} ({tag})...")
    table = pq.read_table(parquet_path)
    pyd = table.to_pydict()
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
                    with open(out_path, "wb") as f: f.write(b)
            extracted_human += 1
        elif lbl == 1 and extracted_spoof < max_spoof:
            out_path = os.path.join(ASVSPOOF_DIR, f"{tag}_spoof_{stem}.flac")
            if not os.path.exists(out_path):
                b = audios[i].get('bytes') if isinstance(audios[i], dict) else None
                if b:
                    with open(out_path, "wb") as f: f.write(b)
            extracted_spoof += 1
        if (i + 1) % 2000 == 0 or (i + 1) == len(table):
            print(f"  Processed {i+1}/{len(table)} -> {extracted_human} bona fide, {extracted_spoof} spoof attacks...", flush=True)
    return extracted_human, extracted_spoof

def main():
    print("=" * 75)
    print("VOXGUARD ASVSPOOF WORKSHOPS & MULTI-TRACK INGESTION")
    print("=" * 75)
    
    # 1. ASVspoof 2015
    extract_string_label_parquet(os.path.join(DATA_DIR, "asvspoof2015.parquet"), tag="asv15")
    
    # 2. ASVspoof 2017 & 2017 TTS
    extract_string_label_parquet(os.path.join(DATA_DIR, "asvspoof2017.parquet"), tag="asv17")
    extract_string_label_parquet(os.path.join(DATA_DIR, "asvspoof2017_tts.parquet"), tag="asv17tts")
    
    # 3. ASVspoof 2021 DF (Deepfake track Shard 0 - 410 MB)
    df_url = "https://huggingface.co/datasets/SpeechAntiSpoofingBenchmarks/ASVspoof2021_DF/resolve/main/data/test-00000-of-00080.parquet"
    df_dst = os.path.join(DATA_DIR, "asvspoof2021_df_test_00000.parquet")
    if download_file(df_url, df_dst, "ASVspoof 2021 DF Deepfake Track Shard 0 (410 MB)"):
        extract_numeric_parquet(df_dst, tag="asv21_df_s0", max_spoof=6000)

    # 4. ASVspoof 2021 LA Shard 2 (300 MB)
    la21_s2_url = "https://huggingface.co/datasets/SpeechAntiSpoofingBenchmarks/ASVspoof2021_LA/resolve/main/data/test-00002-of-00024.parquet"
    la21_s2_dst = os.path.join(DATA_DIR, "asvspoof2021_la_test_00002.parquet")
    if download_file(la21_s2_url, la21_s2_dst, "ASVspoof 2021 LA Shard 2 (300 MB)"):
        extract_numeric_parquet(la21_s2_dst, tag="asv21_la_s2", max_spoof=6000)

    # 5. ASVspoof 2019 LA Shard 2 (464 MB)
    la19_s2_url = "https://huggingface.co/datasets/SpeechAntiSpoofingBenchmarks/ASVspoof2019_LA/resolve/main/data/test-00002-of-00009.parquet"
    la19_s2_dst = os.path.join(DATA_DIR, "asvspoof2019_test_0002.parquet")
    if download_file(la19_s2_url, la19_s2_dst, "ASVspoof 2019 LA Shard 2 (464 MB)"):
        extract_numeric_parquet(la19_s2_dst, tag="asv19_s2", max_spoof=6000)
        
    print("\n[ALL WORKSHOP AND DEEPFAKE DATASETS READY FOR FEATURE INGESTION!]")

if __name__ == "__main__":
    main()
