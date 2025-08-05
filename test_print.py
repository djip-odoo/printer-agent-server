import requests
import base64
import json
import time
from concurrent.futures import ThreadPoolExecutor
import urllib3

# Suppress HTTPS warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Target URL
url = "https://localhost:8080/pos/print/"  # Replace with your actual host

# Fake raster data for testing (e.g., "Hello World" as plain text raster-like)
def make_test_payload():
    hello_world_bytes = "Hello World".encode("utf-8")
    raster_base64 = base64.b64encode(hello_world_bytes).decode("utf-8")

    return {
        "raster_base64": raster_base64,
        "width": 384,
        "height": 50,
        "vendor_id": "0fe6",
        "product_id": "811e",
        "cash_drawer": False
    }

# Send single print job
def send_print_job(i):
    payload = make_test_payload()
    try:
        response = requests.post(
            url,
            headers={"Content-Type": "application/json"},
            json=payload,
            verify=False,
            timeout=5
        )
        print(f"[{i}] ✅ {response.status_code}: {response.text.strip()}")
    except Exception as e:
        print(f"[{i}] ❌ ERROR: {e}")

# Config
TOTAL_JOBS = 1
CONCURRENCY = 5
DELAY_BETWEEN = 1  # seconds

def main():
    print(f"🚀 Sending {TOTAL_JOBS} concurrent print jobs...")
    with ThreadPoolExecutor(max_workers=CONCURRENCY) as executor:
        for i in range(TOTAL_JOBS):
            executor.submit(send_print_job, i + 1)
            time.sleep(DELAY_BETWEEN)

if __name__ == "__main__":
    main()
