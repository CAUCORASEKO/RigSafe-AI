from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List
from .database import init_db
from .audit import persist_audit_event, persist_correlated_event
from .correlation import add_event, check_correlation, get_involved_signal_types
import uuid
import logging
import json

# -------------------------------------------------------------------
# Logging configuration
# -------------------------------------------------------------------

logger = logging.getLogger("rigsafe.audit")
logger.setLevel(logging.INFO)

if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter("%(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.propagate = False

# -------------------------------------------------------------------
# FastAPI app
# -------------------------------------------------------------------

app = FastAPI(
    title="RigSafe AI Backend",
    description="Safety signal ingestion backend for offshore oil & gas operations",
    version="0.1.0"
)

# -------------------------------------------------------------------
# Application lifecycle
# -------------------------------------------------------------------

@app.on_event("startup")
def startup_event():
    init_db()

# -------------------------------------------------------------------
# Data models
# -------------------------------------------------------------------

class SafetySignal(BaseModel):
    source_id: str = Field(..., example="gas_sensor_module_01")
    signal_type: str = Field(..., example="gas_concentration")
    value: float = Field(..., example=18.4)
    unit: Optional[str] = Field(default=None, example="ppm")
    location: Optional[str] = Field(default=None, example="compressor_module")
    timestamp: Optional[datetime] = Field(default_factory=datetime.utcnow)

class SafetyResponse(BaseModel):
    status: str
    signal_id: str
    risk_level: str
    severity_score: int = Field(..., ge=0, le=100)
    recommended_action: str
    message: str
    timestamp: datetime


class CorrelatedSafetyEvent(BaseModel):
    """
    Internal data model for correlated safety events.
    
    Represents a detected multi-signal correlation, not a raw signal.
    Correlated events are stored separately from raw signals to maintain
    a clear audit trail of correlation detections for safety-critical
    operations and post-incident analysis.
    """
    event_id: str
    location: str
    correlated_risk_level: str
    correlation_reason: str
    involved_signal_types: List[str]
    timestamp: datetime

# -------------------------------------------------------------------
# Risk evaluation logic
# -------------------------------------------------------------------

def evaluate_risk(signal: SafetySignal) -> tuple[str, str]:
    if signal.signal_type == "gas_concentration":
        if signal.value >= 25:
            return "high", "Gas concentration significantly above expected baseline"
        elif signal.value >= 15:
            return "elevated", "Gas concentration trend deviates from baseline"
        else:
            return "normal", "Gas concentration within expected range"

    if signal.signal_type == "vibration" and signal.value >= 8.0:
        return "elevated", "Abnormal vibration pattern detected"

    return "normal", "Signal within normal operating parameters"

def risk_level_to_severity_score(risk_level: str) -> int:
    return {"normal": 10, "elevated": 50, "high": 90}.get(risk_level, 10)

def risk_level_to_recommended_action(risk_level: str) -> str:
    return {
        "normal": "Monitor",
        "elevated": "Investigate trend",
        "high": "Immediate operator attention required"
    }.get(risk_level, "Monitor")

def log_safety_audit_event(
    signal_id: str,
    signal: SafetySignal,
    risk_level: str,
    severity_score: int,
    recommended_action: str,
    timestamp: datetime
) -> None:
    if risk_level not in {"elevated", "high"}:
        return

    logger.info(json.dumps({
        "signal_id": signal_id,
        "source_id": signal.source_id,
        "signal_type": signal.signal_type,
        "value": signal.value,
        "location": signal.location,
        "risk_level": risk_level,
        "severity_score": severity_score,
        "recommended_action": recommended_action,
        "timestamp": timestamp.isoformat()
    }))

# -------------------------------------------------------------------
# API endpoints
# -------------------------------------------------------------------

@app.get("/", tags=["System"])
def root():
    return {"message": "RigSafe AI backend is running"}

@app.get("/health", tags=["System"])
def health_check():
    return {
        "status": "ok",
        "service": "rigsafe-backend",
        "timestamp": datetime.utcnow()
    }

@app.post("/signals/ingest", response_model=SafetyResponse, tags=["Signals"])
def ingest_signal(signal: SafetySignal):
    if signal.value < 0:
        raise HTTPException(status_code=400, detail="Signal value must be non-negative")

    # Step 1: Individual risk
    risk_level, message = evaluate_risk(signal)
    severity_score = risk_level_to_severity_score(risk_level)
    recommended_action = risk_level_to_recommended_action(risk_level)

    signal_id = str(uuid.uuid4())[:8]
    timestamp = datetime.utcnow()
    location = signal.location or ""

    # Step 2: Correlation window update
    add_event(location, signal.signal_type, risk_level, timestamp)

    # Step 3: Correlation check
    correlated_level, correlation_reason = check_correlation(
        location, signal.signal_type, risk_level, timestamp
    )

    # Step 4: Risk escalation (ONLY upwards)
    # Correlation ONLY elevates risk, never reduces it. This ensures that
    # multi-signal patterns indicating developing hazardous situations
    # are always treated as high-priority safety events requiring immediate
    # operator attention, even if individual signals might appear less severe.
    if correlated_level == "high":
        risk_level = "high"
        severity_score = 90
        recommended_action = "Immediate operator attention required"
        message = correlation_reason
        
        # Persist correlated event separately from raw signals
        # Correlated events are stored separately to maintain a clear audit
        # trail of multi-signal correlation detections for safety-critical
        # operations, regulatory compliance, and post-incident analysis.
        correlated_event_id = str(uuid.uuid4())[:8]
        involved_types = get_involved_signal_types(location, timestamp)
        persist_correlated_event(
            event_id=correlated_event_id,
            location=location,
            correlated_risk_level=correlated_level,
            correlation_reason=correlation_reason,
            involved_signal_types=involved_types,
            timestamp=timestamp
        )

    # Step 5: Audit & persistence
    if risk_level in {"elevated", "high"}:
        log_safety_audit_event(
            signal_id, signal, risk_level,
            severity_score, recommended_action, timestamp
        )

        persist_audit_event(
            signal_id=signal_id,
            source_id=signal.source_id,
            signal_type=signal.signal_type,
            value=signal.value,
            risk_level=risk_level,
            severity_score=severity_score,
            recommended_action=recommended_action,
            timestamp=timestamp
        )

    return SafetyResponse(
        status="accepted",
        signal_id=signal_id,
        risk_level=risk_level,
        severity_score=severity_score,
        recommended_action=recommended_action,
        message=message,
        timestamp=timestamp
    )


@app.get("/events/correlated", response_model=List[CorrelatedSafetyEvent], tags=["Events"])
def get_correlated_events(limit: int = 50):
    """
    Retrieve the most recent correlated safety events.
    
    Returns correlated events ordered by timestamp descending, intended
    for control-room desktop application consumption. Correlated events
    represent multi-signal correlation detections, stored separately
    from raw signals to maintain a clear audit trail.
    
    Args:
        limit: Maximum number of events to return (default: 50)
    
    Returns:
        List of correlated safety events ordered by timestamp descending
    """
    from .database import get_connection
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT
            event_id,
            location,
            correlated_risk_level,
            correlation_reason,
            involved_signal_types,
            timestamp
        FROM correlated_events
        ORDER BY timestamp DESC
        LIMIT ?
    """, (limit,))
    
    rows = cursor.fetchall()
    conn.close()
    
    events = []
    for row in rows:
        event_id, location, correlated_risk_level, correlation_reason, signal_types_str, timestamp_str = row
        # Parse comma-separated signal types back to list
        involved_signal_types = signal_types_str.split(",") if signal_types_str else []
        # Parse timestamp string back to datetime
        timestamp = datetime.fromisoformat(timestamp_str)
        
        events.append(CorrelatedSafetyEvent(
            event_id=event_id,
            location=location,
            correlated_risk_level=correlated_risk_level,
            correlation_reason=correlation_reason,
            involved_signal_types=involved_signal_types,
            timestamp=timestamp
        ))
    
    return events