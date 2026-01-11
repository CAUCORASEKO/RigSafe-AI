"""
RigSafe-AI Signal Simulator

Demonstrates end-to-end multi-signal correlation detection for safety-critical
offshore oil & gas operations. The simulator sends multiple signals to trigger
correlation rules and verifies that correlated events are properly detected
and persisted.

This simulator is deterministic - it uses fixed delays and clear ordering
to ensure reproducible results suitable for safety audits.
"""

import time
import requests
from datetime import datetime
from typing import Dict, Any

# Backend API endpoints
BASE_URL = "http://127.0.0.1:8000"
INGEST_URL = f"{BASE_URL}/signals/ingest"
CORRELATED_EVENTS_URL = f"{BASE_URL}/events/correlated"

# Simulation configuration
LOCATION = "compressor_module"


def send_signal(
    source_id: str,
    signal_type: str,
    value: float,
    unit: str = "ppm",
    location: str = LOCATION
) -> Dict[str, Any]:
    payload = {
        "source_id": source_id,
        "signal_type": signal_type,
        "value": value,
        "unit": unit,
        "location": location,
        "timestamp": datetime.utcnow().isoformat()
    }
    response = requests.post(INGEST_URL, json=payload)
    response.raise_for_status()
    return response.json()


def print_signal_result(signal_type: str, value: float, result: Dict[str, Any]):
    risk_level = result.get("risk_level", "unknown")
    message = result.get("message", "")
    severity = result.get("severity_score", 0)

    correlation_indicator = ""
    if "correlated" in message.lower():
        correlation_indicator = " [CORRELATION DETECTED]"

    print(
        f"  [{signal_type}] value={value:.2f} → "
        f"risk={risk_level} (severity={severity}){correlation_indicator}"
    )
    print(f"    Message: {message}")


def get_correlated_events() -> list:
    response = requests.get(CORRELATED_EVENTS_URL, params={"limit": 50})
    response.raise_for_status()
    return response.json()


def print_correlated_events(events: list):
    if not events:
        print("  No correlated events found.")
        return

    print(f"  Found {len(events)} correlated event(s):\n")
    for i, event in enumerate(events, 1):
        print(f"  [{i}] Event ID: {event['event_id']}")
        print(f"      Location: {event['location']}")
        print(f"      Risk Level: {event['correlated_risk_level']}")
        print(f"      Signal Types: {', '.join(event['involved_signal_types'])}")
        print(f"      Reason: {event['correlation_reason']}")
        print(f"      Timestamp: {event['timestamp']}")
        print()


def run_correlation_simulation():
    print("=" * 70)
    print("RigSafe-AI Multi-Signal Correlation Simulator")
    print("=" * 70)

    # ------------------------------------------------------------------
    # Phase 1 — Baseline
    # ------------------------------------------------------------------
    print("\nPhase 1: Baseline Normal Signals\n")
    for i in range(3):
        value = 8.0 + i * 0.5
        result = send_signal(
            f"gas_sensor_{i+1:02d}",
            "gas_concentration",
            value
        )
        print_signal_result("gas_concentration", value, result)
        time.sleep(2)

    # ------------------------------------------------------------------
    # Phase 2 — Rule 3 (3+ elevated events)
    # ------------------------------------------------------------------
    print("\nPhase 2: Correlation Trigger — Rule 3 (3+ events)\n")

    for i, value in enumerate([18.5, 19.0, 20.0], 1):
        result = send_signal(
            f"gas_sensor_corr_{i:02d}",
            "gas_concentration",
            value
        )
        print_signal_result("gas_concentration", value, result)
        time.sleep(30)

    # ------------------------------------------------------------------
    # Phase 3 — Mixed signal Rule 3
    # ------------------------------------------------------------------
    print("\nPhase 3: Mixed Signal Correlation (Rule 3)\n")

    for i, value in enumerate([8.5, 9.0, 9.5], 1):
        result = send_signal(
            f"vib_sensor_{i:02d}",
            "vibration",
            value
        )
        print_signal_result("vibration", value, result)
        time.sleep(40)

    # ------------------------------------------------------------------
    # Phase 4 — Retrieve correlated events
    # ------------------------------------------------------------------
    print("\nPhase 4: Retrieve Correlated Events\n")
    time.sleep(1)
    events = get_correlated_events()
    print_correlated_events(events)

    # ------------------------------------------------------------------
    # Phase 5 — Rule 1 (Gas + Temperature)
    # ------------------------------------------------------------------
    print("\nPhase 5: Gas + Temperature Correlation (Rule 1)\n")

    gas = send_signal(
        "gas_rule1_01",
        "gas_concentration",
        18.0
    )
    print_signal_result("gas_concentration", 18.0, gas)
    time.sleep(30)

    temp = send_signal(
        "temp_rule1_01",
        "temperature",
        75.0,
        unit="C"
    )
    print_signal_result("temperature", 75.0, temp)

    # ------------------------------------------------------------------
    # Phase 6 — Rule 2 (Vibration + Pressure)
    # ------------------------------------------------------------------
    print("\nPhase 6: Vibration + Pressure Correlation (Rule 2)\n")

    vib = send_signal(
        "vib_rule2_01",
        "vibration",
        8.8
    )
    print_signal_result("vibration", 8.8, vib)
    time.sleep(30)

    press = send_signal(
        "press_rule2_01",
        "pressure",
        120.0,
        unit="bar"
    )
    print_signal_result("pressure", 120.0, press)

    print("\nSimulation complete.")
    print("=" * 70)


if __name__ == "__main__":
    run_correlation_simulation()