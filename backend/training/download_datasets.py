"""
Download and generate real multi-platform AI voices:
1. OpenAI TTS (ChatGPT / GPT-4o voice) from Hugging Face traderpedroso/openaitts
2. Google & Gemini Neural Voice from gTTS & Google Voice
3. Microsoft Azure / Copilot / Claude-style Neural LLM speech from edge-tts
4. ElevenLabs multi-speaker voice library from Hugging Face Bluebomber182/Elevenlabs-Voices
5. ASVspoof 2017, 2015, and TTS challenge benchmark datasets
6. Genuine multi-speaker human audio (ASVspoof authentic + LibriSpeech human speakers)
"""

import os
import sys
import io
import asyncio
import requests
import pyarrow.parquet as pq
import soundfile as sf

sys.stdout.reconfigure(encoding='utf-8')

TRAIN_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "training_data"))
ASVSPOOF_DIR = os.path.join(TRAIN_DIR, "asvspoof")
AI_DIR = os.path.join(TRAIN_DIR, "ai_online")
HUMAN_DIR = os.path.join(TRAIN_DIR, "human_bonafide")

os.makedirs(ASVSPOOF_DIR, exist_ok=True)
os.makedirs(AI_DIR, exist_ok=True)
os.makedirs(HUMAN_DIR, exist_ok=True)

HEADERS = {"User-Agent": "VoxGuard-Trainer/2.0"}

def download_file(url: str, dest_path: str):
    if os.path.exists(dest_path) and os.path.getsize(dest_path) > 1000:
        return
    try:
        res = requests.get(url, headers=HEADERS, stream=True, timeout=30)
        res.raise_for_status()
        with open(dest_path, "wb") as f:
            for chunk in res.iter_content(chunk_size=512 * 1024):
                if chunk:
                    f.write(chunk)
    except Exception as e:
        print(f"  [WARN] Failed to download {url}: {e}")

# ── 1. OpenAI (ChatGPT / GPT-4o Voice) Collection ──
def collect_openai_tts(max_samples: int = 60):
    print(f"\n[COLLECTING] OpenAI (ChatGPT / GPT-4o) voices from traderpedroso/openaitts...")
    api_url = "https://huggingface.co/api/datasets/traderpedroso/openaitts/tree/main/wavs"
    try:
        r = requests.get(api_url, headers=HEADERS, timeout=15)
        if r.status_code != 200:
            print(f"  API response: {r.status_code}")
            return
        items = r.json()
        downloaded = 0
        for item in items:
            if downloaded >= max_samples:
                break
            path = item.get("path")
            fname = os.path.basename(path)
            dest = os.path.join(AI_DIR, f"openai_{fname}")
            if os.path.exists(dest) and os.path.getsize(dest) > 1000:
                downloaded += 1
                continue
            raw_url = f"https://huggingface.co/datasets/traderpedroso/openaitts/resolve/main/{path}"
            download_file(raw_url, dest)
            if os.path.exists(dest) and os.path.getsize(dest) > 1000:
                downloaded += 1
                if downloaded % 10 == 0:
                    print(f"  Downloaded {downloaded}/{max_samples} OpenAI voice samples...")
        print(f"  OpenAI TTS collection complete: {downloaded} samples.")
    except Exception as e:
        print(f"  OpenAI collection error: {e}")

# ── 2. ElevenLabs Multi-Speaker Collection ──
def collect_elevenlabs_hf():
    print(f"\n[COLLECTING] ElevenLabs multi-speaker files from Bluebomber182/Elevenlabs-Voices...")
    api_url = "https://huggingface.co/api/datasets/Bluebomber182/Elevenlabs-Voices/tree/main"
    try:
        r = requests.get(api_url, headers=HEADERS, timeout=15)
        if r.status_code != 200:
            return
        # Download compressed formats (< 5MB each)
        items = [x for x in r.json() if x.get("path", "").endswith((".ogg", ".opus")) and x.get("size", 0) < 6000000]
        downloaded = 0
        for item in items:
            path = item.get("path")
            fname = os.path.basename(path).replace(" ", "_")
            dest = os.path.join(AI_DIR, f"elevenlabs_lib_{fname}")
            if os.path.exists(dest) and os.path.getsize(dest) > 1000:
                downloaded += 1
                continue
            # URL encode spaces in path
            safe_path = requests.utils.quote(path)
            raw_url = f"https://huggingface.co/datasets/Bluebomber182/Elevenlabs-Voices/resolve/main/{safe_path}"
            print(f"  Downloading ElevenLabs voice: {fname} ({item.get('size', 0):,} bytes)...")
            download_file(raw_url, dest)
            if os.path.exists(dest) and os.path.getsize(dest) > 1000:
                downloaded += 1
        print(f"  ElevenLabs collection complete: {downloaded} rich multi-speaker files.")
    except Exception as e:
        print(f"  ElevenLabs collection error: {e}")

# ── 3. Microsoft Azure / Copilot / Claude-Style Neural Speech (edge-tts) ──
async def generate_neural_edge_tts():
    print(f"\n[GENERATING] Modern Neural Voices (Claude/Copilot/Azure Neural engine)...")
    try:
        import edge_tts
    except ImportError:
        print("  edge-tts not installed, skipping.")
        return

    VOICES = [
        "en-US-JennyNeural",
        "en-US-GuyNeural",
        "en-US-AriaNeural",
        "en-US-ChristopherNeural",
        "en-US-EricNeural",
        "en-US-MichelleNeural",
        "en-GB-SoniaNeural",
        "en-GB-RyanNeural",
        "en-IN-NeerjaNeural",
        "en-IN-PrabhatNeural",
        "en-AU-NatashaNeural",
        "en-CA-ClaraNeural"
    ]

    PROMPTS = [
        "Good afternoon, I am calling regarding the urgent transaction update on your checking account.",
        "Your verification code has been confirmed. Please hold the line while our automated system authorizes the request.",
        "This is an automated intelligence notification from the compliance department. Please confirm your identity.",
        "Thank you for contacting customer support. All representatives are currently busy assisting other callers.",
        "Hello, this is your AI voice assistant. How may I assist you with your security configurations today?",
        "Security alert: unusual login detected from a new IP address. If this was not you, press one now."
    ]

    count = 0
    for voice in VOICES:
        for p_idx, text in enumerate(PROMPTS[:3]):
            dest = os.path.join(AI_DIR, f"neural_{voice}_{p_idx}.mp3")
            if os.path.exists(dest) and os.path.getsize(dest) > 1000:
                count += 1
                continue
            try:
                comm = edge_tts.Communicate(text, voice)
                await comm.save(dest)
                count += 1
            except Exception as e:
                pass
    print(f"  Neural speech generation complete: {count} samples generated.")

# ── 4. Google & Gemini Speech (gTTS) ──
def generate_google_tts():
    print(f"\n[GENERATING] Google Text-to-Speech & Gemini Voice samples...")
    try:
        from gtts import gTTS
    except ImportError:
        print("  gTTS not installed, skipping.")
        return

    TLDS = ["com", "co.uk", "ca", "co.in", "com.au"]
    PROMPTS = [
        "Hello, this is the Google Assistant automated verification service calling to confirm your appointment.",
        "We detected an unauthorized login attempt from a new device in your area. Immediate confirmation is required.",
        "Your payment has been successfully processed by the automated billing platform.",
        "Please listen carefully as our menu options have recently changed for customer service.",
        "This is Gemini voice live dialogue system. All systems are operational and connected.",
        "Voice authentication required. Please state your account number and passkey clearly."
    ]

    count = 0
    for tld in TLDS:
        for p_idx, text in enumerate(PROMPTS):
            dest = os.path.join(AI_DIR, f"google_tts_{tld}_{p_idx}.mp3")
            if os.path.exists(dest) and os.path.getsize(dest) > 1000:
                count += 1
                continue
            try:
                tts = gTTS(text, lang="en", tld=tld)
                tts.save(dest)
                count += 1
            except Exception:
                pass
    print(f"  Google TTS generation complete: {count} samples generated.")

# ── 5. Extract LibriSpeech Real Human Audio ──
def extract_librispeech_bonafide():
    parquet_path = os.path.join(TRAIN_DIR, "librispeech_human.parquet")
    if not os.path.exists(parquet_path):
        return
    print(f"\n[EXTRACTING] LibriSpeech Genuine Human Speakers from {os.path.basename(parquet_path)}...")
    try:
        table = pq.read_table(parquet_path)
        d = table.to_pydict()
        audios = d.get('audio', [])
        extracted = 0
        for idx, item in enumerate(audios):
            dest = os.path.join(HUMAN_DIR, f"librispeech_human_{idx}.wav")
            if os.path.exists(dest) and os.path.getsize(dest) > 1000:
                extracted += 1
                continue
            if isinstance(item, dict) and 'bytes' in item:
                audio_bytes = item['bytes']
            elif isinstance(item, bytes):
                audio_bytes = item
            else:
                continue
            if audio_bytes and len(audio_bytes) > 500:
                with open(dest, "wb") as f:
                    f.write(audio_bytes)
                extracted += 1
        print(f"  LibriSpeech human extraction complete: {extracted} bona fide human speakers extracted.")
    except Exception as e:
        print(f"  LibriSpeech extraction error: {e}")

# ── 6. Local Verified Samples (Downloads & test_samples) ──
def collect_local_verified_samples():
    user_downloads = os.path.expanduser(r"~\Downloads")
    test_samples_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "test_samples"))

    if os.path.exists(user_downloads):
        for fname in os.listdir(user_downloads):
            fpath = os.path.join(user_downloads, fname)
            if not os.path.isfile(fpath): continue
            lower = fname.lower()
            if "elevenlabs" in lower and lower.endswith((".mp3", ".wav", ".mp4")):
                dest = os.path.join(AI_DIR, fname)
                if not os.path.exists(dest):
                    with open(fpath, "rb") as s, open(dest, "wb") as d: d.write(s.read())
            elif ("human" in lower or "whatsapp" in lower) and lower.endswith((".mp4", ".wav", ".mp3", ".ogg")):
                dest = os.path.join(HUMAN_DIR, fname)
                if not os.path.exists(dest):
                    with open(fpath, "rb") as s, open(dest, "wb") as d: d.write(s.read())

    if os.path.exists(test_samples_dir):
        for fname in os.listdir(test_samples_dir):
            fpath = os.path.join(test_samples_dir, fname)
            if not os.path.isfile(fpath): continue
            lower = fname.lower()
            if ("google_voice" in lower or "ai_voice" in lower) and lower.endswith((".mp3", ".wav", ".mp4")):
                dest = os.path.join(AI_DIR, fname)
                if not os.path.exists(dest):
                    with open(fpath, "rb") as s, open(dest, "wb") as d: d.write(s.read())
            elif "human" in lower and lower.endswith((".mp3", ".wav", ".mp4")):
                dest = os.path.join(HUMAN_DIR, fname)
                if not os.path.exists(dest):
                    with open(fpath, "rb") as s, open(dest, "wb") as d: d.write(s.read())

# ── 7. ASVspoof Extraction ──
def extract_asvspoof_samples(parquet_path: str, max_samples: int = 190):
    if not os.path.exists(parquet_path): return
    print(f"\n[EXTRACTING] Reading {os.path.basename(parquet_path)}...")
    table = pq.read_table(parquet_path)
    data_dict = table.to_pydict()
    labels = data_dict.get('label', [])
    audios = data_dict.get('audio', [])
    num_rows = table.num_rows

    extracted_spoof = 0
    extracted_human = 0
    prefix = os.path.basename(parquet_path).split('.')[0]

    for idx in range(num_rows):
        label = str(labels[idx] if idx < len(labels) else '').lower().strip()
        if any(w in label for w in ['authentic', 'bonafide', 'human', 'genuine']) or label == '0':
            cat = "bonafide"
        else:
            cat = "spoof"

        audio_entry = audios[idx] if idx < len(audios) else None
        if not audio_entry: continue

        audio_bytes = None
        if isinstance(audio_entry, dict) and 'bytes' in audio_entry:
            audio_bytes = audio_entry['bytes']
        elif isinstance(audio_entry, bytes):
            audio_bytes = audio_entry

        if not audio_bytes or len(audio_bytes) < 500: continue

        if cat == "bonafide" and extracted_human < max_samples:
            target = os.path.join(HUMAN_DIR, f"{prefix}_human_{idx}.wav")
            if not os.path.exists(target):
                with open(target, "wb") as f: f.write(audio_bytes)
            extracted_human += 1
        elif cat == "spoof" and extracted_spoof < max_samples:
            target = os.path.join(ASVSPOOF_DIR, f"{prefix}_spoof_{idx}.wav")
            if not os.path.exists(target):
                with open(target, "wb") as f: f.write(audio_bytes)
            extracted_spoof += 1

        if extracted_spoof >= max_samples and extracted_human >= max_samples:
            break

if __name__ == "__main__":
    print("=" * 70)
    print("VOXGUARD MULTI-PLATFORM AI VOICE & BENCHMARK DATASET COLLECTION")
    print("=" * 70)

    # 1. Local verified samples
    collect_local_verified_samples()

    # 2. OpenAI TTS (ChatGPT / GPT-4o voice)
    collect_openai_tts(max_samples=60)

    # 3. ElevenLabs Library
    collect_elevenlabs_hf()

    # 4. Neural Edge TTS (Azure / Copilot / Claude-style neural voices)
    asyncio.run(generate_neural_edge_tts())

    # 5. Google TTS & Gemini voices
    generate_google_tts()

    # 6. LibriSpeech authentic human speakers
    extract_librispeech_bonafide()

    # 7. ASVspoof benchmarks
    for pq_name in ["asvspoof2017.parquet", "asvspoof2015.parquet", "asvspoof2017_tts.parquet"]:
        p = os.path.join(TRAIN_DIR, pq_name)
        if os.path.exists(p):
            extract_asvspoof_samples(p, max_samples=190)

    print("\n" + "=" * 70)
    print("DATASET COLLECTION SUMMARY:")
    print("=" * 70)
    print(f"  AI Voices (OpenAI GPT, Google/Gemini, Azure/Claude, ElevenLabs): {len(os.listdir(AI_DIR))} files")
    print(f"  ASVspoof Challenge Benchmark Attacks:                          {len(os.listdir(ASVSPOOF_DIR))} files")
    print(f"  Bona Fide Human Speakers (ASVspoof + LibriSpeech + Live):      {len(os.listdir(HUMAN_DIR))} files")
