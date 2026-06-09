#!/usr/bin/env python3
import os
import sys
import time
from dotenv import load_dotenv

# Ensure we can run this from the project root or tools directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.batch_pipeline import run_batch_pipeline

# Load env variables from .env
load_dotenv()

def main():
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        stream=sys.stdout
    )
    batches = [
        ("data/daily_logs/2026-06-05_log.csv", "2026-06-05"),
        ("data/daily_logs/2026-06-06_log.csv", "2026-06-06"),
        ("data/daily_logs/2026-06-07_log.csv", "2026-06-07"),
        ("data/daily_logs/2026-06-12_log.csv", "2026-06-12"),
    ]

    total_start = time.perf_counter()
    print("=" * 80)
    print("STARTING RUN OF ALL JUNE 2026 BATCH LOGS")
    print("=" * 80)

    for file_path, batch_date in batches:
        if not os.path.exists(file_path):
            print(f"Error: Log file not found at {file_path}. Skipping.")
            continue
            
        print(f"\nProcessing Batch Date: {batch_date} from {file_path}...")
        try:
            summary = run_batch_pipeline(file_path, batch_date)
            print("-" * 50)
            print(f"Success for {batch_date}:")
            print(f"  Total Records Scored: {summary.get('total_records')}")
            print(f"  Total Users Processed: {summary.get('total_users')}")
            print(f"  Anomalies Detected: {summary.get('anomalies_detected')}")
            print(f"  Alerts Generated: {summary.get('alerts_generated')}")
            print(f"  Processing Time: {summary.get('processing_time_seconds')}s")
            print(f"  Email Audit Status: {summary.get('email_audits_status')}")
            print(f"  Email Audited Count: {summary.get('email_audited_count')}")
            print("-" * 50)
        except Exception as e:
            print(f"FAILED for {batch_date}: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 80)
    print(f"ALL BATCHES PROCESSING COMPLETED IN {time.perf_counter() - total_start:.2f}s")
    print("=" * 80)

if __name__ == "__main__":
    main()
