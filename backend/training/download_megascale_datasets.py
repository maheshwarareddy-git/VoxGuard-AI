import os
import sys
import json
import requests
import pyarrow.parquet as pq
import io
import soundfile as sf
import numpy as np

HUMAN_DIR = r"c:\Users\mahesh\Desktop\VoxGuard\training_data\human_bonafide"
AI_DIR = r"c:\Users\mahesh\Desktop\VoxGuard\training_data\ai_online"
os.makedirs(HUMAN_DIR, exist_ok=True)
os.makedirs(AI_DIR, exist_ok=True)

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

def download_file(url, dest_path):
    if os.path.exists(dest_path) and os.path.getsize(dest_path) > 1000:
        print(f"Already exists: {os.path.basename(dest_path)}")
        return True
    try:
        print(f"Downloading {url} ...")
        r = requests.get(url, headers=HEADERS, stream=True, timeout=120)
        r.raise_for_status()
        with open(dest_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                if chunk: f.write(chunk)
        print(f"Saved {os.path.basename(dest_path)} ({os.path.getsize(dest_path) / (1024*1024):.2f} MB)")
        return True
    except Exception as e:
        print(f"Failed to download {url}: {e}")
        return False

# ─── 1. Hemg/Deepfake-Audio-Dataset (85 MB) ───
print("\n=== 1. Processing Hemg/Deepfake-Audio-Dataset ===")
hemg_url = "https://huggingface.co/datasets/Hemg/Deepfake-Audio-Dataset/resolve/refs%2Fconvert%2Fparquet/default/train/0000.parquet"
hemg_parquet = r"c:\Users\mahesh\Desktop\VoxGuard\training_data\hemg_deepfake.parquet"
if download_file(hemg_url, hemg_parquet):
    try:
        table = pq.read_table(hemg_parquet)
        pyd = table.to_pydict()
        audios = pyd.get("audio", [])
        labels = pyd.get("label", [])
        print(f"Loaded Hemg dataset: {len(audios)} audio records")
        # In Hemg dataset: Label 0 = Fake, Label 1 = Real
        fake_count = 0
        real_count = 0
        for idx, (audio_obj, lbl) in enumerate(zip(audios, labels)):
            if isinstance(audio_obj, dict) and "bytes" in audio_obj:
                raw_bytes = audio_obj["bytes"]
            else:
                continue
            if not raw_bytes or len(raw_bytes) < 1000: continue
            
            if lbl == 1: # Real human
                out_path = os.path.join(HUMAN_DIR, f"hemg_real_{idx}.wav")
                with open(out_path, "wb") as f: f.write(raw_bytes)
                real_count += 1
            else: # Deepfake AI
                out_path = os.path.join(AI_DIR, f"hemg_fake_{idx}.wav")
                with open(out_path, "wb") as f: f.write(raw_bytes)
                fake_count += 1
        print(f"Extracted Hemg: {real_count} real human files, {fake_count} deepfake AI files")
    except Exception as e:
        print(f"Error parsing Hemg parquet: {e}")

# ─── 2. UniDataPro Real vs Fake Human Voice ───
print("\n=== 2. Processing UniDataPro/real-vs-fake-human-voice-deepfake-audio ===")
try:
    api_url = "https://huggingface.co/api/datasets/UniDataPro/real-vs-fake-human-voice-deepfake-audio"
    r = requests.get(api_url, headers=HEADERS, timeout=15)
    unidata_info = r.json()
    siblings = [s["rfilename"] for s in unidata_info.get("siblings", []) if s["rfilename"].endswith((".m4a", ".mp3", ".wav"))]
    print(f"Found {len(siblings)} files in UniDataPro")
    
    unidata_real = 0
    unidata_fake = 0
    for rel_path in siblings:
        safe_name = rel_path.replace("/", "_").replace("\\", "_")
        dl_url = f"https://huggingface.co/datasets/UniDataPro/real-vs-fake-human-voice-deepfake-audio/resolve/main/{rel_path}"
        if "original" in rel_path.lower():
            target_file = os.path.join(HUMAN_DIR, f"unidata_real_{safe_name}")
            if download_file(dl_url, target_file): unidata_real += 1
        elif "synthetic" in rel_path.lower():
            target_file = os.path.join(AI_DIR, f"unidata_fake_{safe_name}")
            if download_file(dl_url, target_file): unidata_fake += 1
    print(f"Downloaded UniDataPro: {unidata_real} real human files, {unidata_fake} synthetic clone files")
except Exception as e:
    print(f"Error downloading UniDataPro: {e}")

# ─── 3. PolyAI/minds14 Multilingual Human Voices (Spanish, French, German) ───
print("\n=== 3. Processing PolyAI/minds14 Multilingual (es-ES, fr-FR, de-DE) ===")
minds_configs = [
    ("es_es", "https://huggingface.co/datasets/PolyAI/minds14/resolve/refs%2Fconvert%2Fparquet/es-ES/train/0000.parquet"),
    ("fr_fr", "https://huggingface.co/datasets/PolyAI/minds14/resolve/refs%2Fconvert%2Fparquet/fr-FR/train/0000.parquet"),
    ("de_de", "https://huggingface.co/datasets/PolyAI/minds14/resolve/refs%2Fconvert%2Fparquet/de-DE/train/0000.parquet")
]

for cfg, url in minds_configs:
    pq_path = rf"c:\Users\mahesh\Desktop\VoxGuard\training_data\minds14_{cfg}.parquet"
    if download_file(url, pq_path):
        try:
            table = pq.read_table(pq_path)
            audios = table.to_pydict().get("audio", [])
            print(f"Loaded {cfg}: {len(audios)} human speaker recordings")
            c = 0
            for idx, item in enumerate(audios):
                if isinstance(item, dict) and "bytes" in item:
                    raw_bytes = item["bytes"]
                    if raw_bytes and len(raw_bytes) > 2000:
                        out_p = os.path.join(HUMAN_DIR, f"minds14_{cfg}_{idx}.wav")
                        with open(out_p, "wb") as f: f.write(raw_bytes)
                        c += 1
            print(f"Extracted {c} human recordings for {cfg}")
        except Exception as e:
            print(f"Error parsing {cfg} parquet: {e}")

# ─── 4. Additional OpenAI TTS Samples ───
print("\n=== 4. Fetching Additional OpenAI TTS Samples ===")
try:
    api_url = "https://huggingface.co/api/datasets/traderpedroso/openaitts"
    r = requests.get(api_url, headers=HEADERS, timeout=15)
    openaitts_info = r.json()
    wav_files = [s["rfilename"] for s in openaitts_info.get("siblings", []) if s["rfilename"].startswith("wavs/") and s["rfilename"].endswith(".wav")]
    print(f"Found {len(wav_files)} OpenAI TTS files on repo")
    # Download next 150 files
    downloaded = 0
    for rel_p in wav_files[150:300]:
        fname = os.path.basename(rel_p)
        dest = os.path.join(AI_DIR, f"openai_extra_{fname}")
        url = f"https://huggingface.co/datasets/traderpedroso/openaitts/resolve/main/{rel_p}"
        if download_file(url, dest):
            downloaded += 1
    print(f"Downloaded {downloaded} additional OpenAI TTS samples")
except Exception as e:
    print(f"Error fetching extra OpenAI samples: {e}")

print("\n=== Dataset Ingestion Summary ===")
total_human = len([f for f in os.listdir(HUMAN_DIR) if os.path.getsize(os.path.join(HUMAN_DIR, f)) > 1000])
total_ai = len([f for f in os.listdir(AI_DIR) if os.path.getsize(os.path.join(AI_DIR, f)) > 1000])
print(f"Total Authentic Human Files on Disk: {total_human}")
print(f"Total AI Synthetic Files on Disk:   {total_ai}")
print(f"Combined Audio Corpus:              {total_human + total_ai} full recordings")
