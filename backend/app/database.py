import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "audit.db"

def get_connection():
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS safety_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            signal_id TEXT NOT NULL,
            source_id TEXT NOT NULL,
            signal_type TEXT NOT NULL,
            value REAL NOT NULL,
            risk_level TEXT NOT NULL,
            severity_score INTEGER NOT NULL,
            recommended_action TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
    """)

    # Correlated events are stored separately from raw signals to maintain
    # a clear audit trail of multi-signal correlation detections.
    # This separation ensures that correlation analysis remains explainable
    # and auditable, which is critical for safety-critical systems.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS correlated_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id TEXT NOT NULL UNIQUE,
            location TEXT NOT NULL,
            correlated_risk_level TEXT NOT NULL,
            correlation_reason TEXT NOT NULL,
            involved_signal_types TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()