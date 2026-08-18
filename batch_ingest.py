"""
batch_ingest.py — Batch ingestion runner for dataset.csv.
Reads rows from dataset.csv and dispatches enrichment jobs to the FastAPI cluster.
"""
import csv
import time
import httpx
import os

API_URL = os.getenv("API_URL", "http://localhost:8000")
CSV_PATH = os.getenv("CSV_PATH", "dataset.csv")

def run_batch(limit: int = None, delay: float = 0.05):
    print("=" * 60)
    print(f"Project Unilog: Batch Ingestion from {CSV_PATH}")
    print(f"Target API: {API_URL}")
    print("=" * 60)

    if not os.path.exists(CSV_PATH):
        print(f"Error: {CSV_PATH} not found.")
        return

    items = []
    with open(CSV_PATH, "r", encoding="utf-8", errors="replace") as f:
        reader = csv.reader(f)
        for row in reader:
            if not row or len(row) < 3:
                continue
            # Header check
            if "Mfg_Part_Num" in row or "MFR URL" in row:
                continue
            
            # Extract MPN, Manuf, Brand, URL from CSV layout
            # Standard row layout from user CSV:
            # Col 0: MFR URL (if full row) or Mfg_Part_Num (if short row)
            mpn = ""
            manuf = ""
            brand = ""
            mfr_url = None

            if len(row) > 16 and row[0].startswith("http"):
                # Full 100+ col row format
                mfr_url = row[0]
                mpn = row[11] or row[20]
                manuf = row[17] or row[16]
                brand = row[18] or ""
            elif len(row) >= 6:
                # 6-col SKU row format: Mfg_Part_Num,Part_Desc,E1_Brand,Unilog_Brand,DIB_Brand,Part_Manuf
                mpn = row[0]
                desc = row[1]
                brand = row[2] if row[2] and not row[2].startswith("--") else (row[4] if not row[4].startswith("--") else "")
                manuf = row[5]
            else:
                mpn = row[0]
                manuf = row[1] if len(row) > 1 else "Unknown"

            if mpn and manuf:
                items.append({
                    "mfg_part_num": mpn.strip(),
                    "manufacturer": manuf.strip(),
                    "brand_name": brand.strip() or "Standard",
                    "mfr_url": mfr_url
                })

    print(f"Loaded {len(items)} product SKUs from {CSV_PATH}.")
    if limit:
        items = items[:limit]
        print(f"Processing first {limit} SKUs...")

    dispatched = 0
    errors = 0

    with httpx.Client(timeout=10) as client:
        # Check health first
        try:
            h = client.get(f"{API_URL}/health")
            print(f"Health Check: {h.status_code} - {h.json()}")
        except Exception as e:
            print(f"Warning: Gateway health check failed ({e}). Attempting ingest anyway...")

        for idx, item in enumerate(items, 1):
            try:
                r = client.post(f"{API_URL}/ingest", json=item)
                if r.status_code == 202:
                    data = r.json()
                    status = data.get("status", "queued")
                    print(f"[{idx}/{len(items)}] {item['mfg_part_num']:<20} ({item['manufacturer'][:25]}) -> HTTP {r.status_code} [{status}]")
                    dispatched += 1
                else:
                    print(f"[{idx}/{len(items)}] {item['mfg_part_num']} -> HTTP {r.status_code}: {r.text}")
                    errors += 1
            except Exception as e:
                print(f"[{idx}/{len(items)}] {item['mfg_part_num']} -> Error: {e}")
                errors += 1

            if delay > 0:
                time.sleep(delay)

    print("-" * 60)
    print(f"Batch Complete: {dispatched} dispatched, {errors} errors.")
    print("Inspect live progress on: http://localhost:8080")

if __name__ == "__main__":
    import sys
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
    run_batch(limit=limit)
