import time
import random
import requests
from datetime import datetime

API_URL = "http://127.0.0.1:8000/signals/ingest"

SOURCE_ID = "gas_sensor_module_01"
SIGNAL_TYPE = "gas_concentration"
UNIT = "ppm"
LOCATION = "compressor_module"


def send_signal(value: float):
    payload = {
        "source_id": SOURCE_ID,
        "signal_type": SIGNAL_TYPE,
        "value": value,
        "unit": UNIT,
        "location": LOCATION,
        "timestamp": datetime.utcnow().isoformat()
    }

    response = requests.post(API_URL, json=payload)
    response.raise_for_status()
    return response.json()


def run_simulation():
    print("Starting RigSafe-AI signal simulator\n")

    # -------------------------------
    # Phase 1: Baseline (normal)
    # -------------------------------
    print("--- Baseline phase ---")
    for _ in range(5):
        value = random.uniform(5.0, 10.0)
        result = send_signal(value)
        print(f"[{datetime.utcnow().isoformat()}] value={value:.2f} | risk={result['risk_level']} | msg={result['message']}")
        time.sleep(1)

    # -------------------------------
    # Phase 2: Elevated trend
    # -------------------------------
    print("\n--- Elevated trend phase ---")
    for _ in range(5):
        value = random.uniform(15.0, 22.0)
        result = send_signal(value)
        print(f"[{datetime.utcnow().isoformat()}] value={value:.2f} | risk={result['risk_level']} | msg={result['message']}")
        time.sleep(1)

    # -------------------------------
    # Phase 3: Anomaly event
    # -------------------------------
    print("\n--- Anomaly event ---")
    value = random.uniform(30.0, 40.0)
    result = send_signal(value)
    print(f"[{datetime.utcnow().isoformat()}] value={value:.2f} | risk={result['risk_level']} | msg={result['message']}")

    print("\nSimulation completed")


if __name__ == "__main__":
    run_simulation()