from datetime import datetime
from typing import List
from .database import get_connection

def persist_audit_event(
    signal_id: str,
    source_id: str,
    signal_type: str,
    value: float,
    risk_level: str,
    severity_score: int,
    recommended_action: str,
    timestamp: datetime
):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO safety_events (
            signal_id,
            source_id,
            signal_type,
            value,
            risk_level,
            severity_score,
            recommended_action,
            timestamp
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        signal_id,
        source_id,
        signal_type,
        value,
        risk_level,
        severity_score,
        recommended_action,
        timestamp.isoformat()
    ))

    conn.commit()
    conn.close()


def persist_correlated_event(
    event_id: str,
    location: str,
    correlated_risk_level: str,
    correlation_reason: str,
    involved_signal_types: List[str],
    timestamp: datetime
):
    """
    Persist a detected correlated safety event to the database.
    
    Correlated events are stored separately from raw signals to maintain
    a clear audit trail of multi-signal correlation detections. This
    separation ensures correlation analysis remains explainable and
    auditable for safety-critical operations.
    
    Correlation ONLY escalates risk, never reduces it. This ensures
    that multi-signal patterns are always treated as high-priority
    safety events requiring immediate operator attention.
    """
    conn = get_connection()
    cursor = conn.cursor()

    # Store signal types as comma-separated list for simplicity
    signal_types_str = ",".join(sorted(involved_signal_types))

    cursor.execute("""
        INSERT INTO correlated_events (
            event_id,
            location,
            correlated_risk_level,
            correlation_reason,
            involved_signal_types,
            timestamp
        ) VALUES (?, ?, ?, ?, ?, ?)
    """, (
        event_id,
        location,
        correlated_risk_level,
        correlation_reason,
        signal_types_str,
        timestamp.isoformat()
    ))

    conn.commit()
    conn.close()