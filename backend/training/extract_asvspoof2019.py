import os
import pyarrow.parquet as pq

BASE_DIR = r"c:\Users\mahesh\Desktop\VoxGuard"
DATA_DIR = os.path.join(BASE_DIR, "training_data")
PARQUET_FILE = os.path.join(DATA_DIR, "asvspoof2019_test_0000.parquet")
HUMAN_DIR = os.path.join(DATA_DIR, "human_bonafide")
ASVSPOOF_DIR = os.path.join(DATA_DIR, "asvspoof")

os.makedirs(HUMAN_DIR, exist_ok=True)
os.makedirs(ASVSPOOF_DIR, exist_ok=True)

def main():
    print(f"Reading ASVspoof 2019 LA shard: {PARQUET_FILE}...")
    table = pq.read_table(PARQUET_FILE)
    print(f"Loaded shard with {len(table):,} rows. Columns: {table.column_names}")

    pyd = table.to_pydict()
    paths = pyd['path']
    audios = pyd['audio']
    labels = pyd['label']

    extracted_human = 0
    extracted_spoof = 0
    spoof_limit = 10000  # Extract all available in shard

    total_rows = len(table)
    print(f"Extracting audio samples (All bonafide humans + {spoof_limit} ASVspoof attacks)...")

    for i in range(total_rows):
        lbl = int(labels[i])
        fname = paths[i]
        stem = os.path.splitext(os.path.basename(fname))[0]

        if lbl == 0:
            out_path = os.path.join(HUMAN_DIR, f"asv19_bona_{stem}.flac")
            if not os.path.exists(out_path):
                audio_item = audios[i]
                b = audio_item.get('bytes') if isinstance(audio_item, dict) else None
                if b:
                    with open(out_path, "wb") as f:
                        f.write(b)
            extracted_human += 1
        elif lbl == 1 and extracted_spoof < spoof_limit:
            out_path = os.path.join(ASVSPOOF_DIR, f"asv19_spoof_{stem}.flac")
            if not os.path.exists(out_path):
                audio_item = audios[i]
                b = audio_item.get('bytes') if isinstance(audio_item, dict) else None
                if b:
                    with open(out_path, "wb") as f:
                        f.write(b)
            extracted_spoof += 1

        if (i + 1) % 1000 == 0 or (i + 1) == total_rows:
            print(f"  Processed {i+1}/{total_rows} rows -> Extracted: {extracted_human} bonafide human, {extracted_spoof} spoof attacks")

    print(f"\n[EXTRACTION COMPLETE]")
    print(f"Extracted ASVspoof 2019 Bona Fide Human: {extracted_human}")
    print(f"Extracted ASVspoof 2019 Benchmark Attacks: {extracted_spoof}")

if __name__ == "__main__":
    main()
