from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from .database import init_db
from .audit import persist_audit_event
from .correlation import add_event, check_correlation
import uuid
import logging
import json

# -------------------------------------------------------------------
# Logging configuration
# -------------------------------------------------------------------

logger = logging.getLogger("rigsafe.audit")
logger.setLevel(logging.INFO)

# Avoid duplicate handlers on module reload
if not logger.handlers:
    # Configure console handler with JSON-formatted output for structured logging
    handler = logging.StreamHandler()
    handler.setLevel(logging.INFO)
    
    # Use a formatter that outputs structured JSON for machine readability
    formatter = logging.Formatter('%(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    # Prevent propagation to root logger to avoid duplicate logs
    logger.propagate = False

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
    """
    Initialize database on application startup.
    Creates SQLite database and safety_events table if they don't exist.
    """
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
    severity_score: int = Field(..., ge=0, le=100, description="Numeric severity score from 0-100")
    recommended_action: str = Field(..., description="Recommended action based on risk level")
    message: str
    timestamp: datetime
    correlated_risk_level: Optional[str] = Field(default=None, description="Correlated risk level detected from multi-signal analysis")
    correlation_reason: Optional[str] = Field(default=None, description="Explanation of the detected correlation")


# -------------------------------------------------------------------
# Simple risk evaluation logic (MVP)
# -------------------------------------------------------------------

def evaluate_risk(signal: SafetySignal) -> tuple[str, str]:
    """
    Simple, explainable, rule-based risk evaluation.
    This logic is intentionally transparent and conservative.
    """

    if signal.signal_type == "gas_concentration":
        if signal.value >= 25:
            return "high", "Gas concentration significantly above expected baseline"
        elif signal.value >= 15:
            return "elevated", "Gas concentration trend deviates from baseline"
        else:
            return "normal", "Gas concentration within expected range"

    if signal.signal_type == "vibration":
        if signal.value >= 8.0:
            return "elevated", "Abnormal vibration pattern detected"

    return "normal", "Signal within normal operating parameters"


def risk_level_to_severity_score(risk_level: str) -> int:
    """
    Map risk level to a numeric severity score (0-100).
    Provides a quantitative measure for downstream systems.
    """
    mapping = {
        "normal": 10,
        "elevated": 50,
        "high": 90
    }
    return mapping.get(risk_level, 10)  # Default to 10 if unknown risk level


def risk_level_to_recommended_action(risk_level: str) -> str:
    """
    Map risk level to a recommended action.
    Provides explicit, explainable guidance for operators based on risk assessment.
    """
    mapping = {
        "normal": "Monitor",
        "elevated": "Investigate trend",
        "high": "Immediate operator attention required"
    }
    return mapping.get(risk_level, "Monitor")  # Default to "Monitor" if unknown risk level


def log_safety_audit_event(
    signal_id: str,
    signal: SafetySignal,
    risk_level: str,
    severity_score: int,
    recommended_action: str,
    timestamp: datetime
) -> None:
    """
    Log structured audit event for safety signals with elevated or high risk levels.
    Provides traceability for post-incident analysis and regulatory compliance.
    """
    if risk_level not in ["elevated", "high"]:
        return  # Only log elevated and high-risk signals
    
    audit_log = {
        "signal_id": signal_id,
        "source_id": signal.source_id,
        "signal_type": signal.signal_type,
        "value": signal.value,
        "risk_level": risk_level,
        "severity_score": severity_score,
        "recommended_action": recommended_action,
        "timestamp": timestamp.isoformat()
    }
    
    # Log as JSON string for machine-readable structured format
    logger.info(json.dumps(audit_log, ensure_ascii=False))


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
    """
    Ingest a safety-relevant signal and return a risk assessment.
    """

    if signal.value < 0:
        raise HTTPException(
            status_code=400,
            detail="Signal value must be non-negative"
        )

    risk_level, message = evaluate_risk(signal)
    severity_score = risk_level_to_severity_score(risk_level)
    recommended_action = risk_level_to_recommended_action(risk_level)
    
    # Generate signal_id and timestamp once for consistency
    signal_id = str(uuid.uuid4())[:8]
    timestamp = datetime.utcnow()
    
    # Add event to correlation window and check for correlations
    location = signal.location or ""
    add_event(location, signal.signal_type, risk_level, timestamp)
    correlated_risk_level, correlation_reason = check_correlation(
        location, signal.signal_type, risk_level, timestamp
    )
    
    # Log and persist audit events for elevated and high-risk signals
    if risk_level in ["elevated", "high"]:
        # Structured JSON logging for machine-readable audit trail
        log_safety_audit_event(
            signal_id=signal_id,
            signal=signal,
            risk_level=risk_level,
            severity_score=severity_score,
            recommended_action=recommended_action,
            timestamp=timestamp
        )
        
        # Persist to database for long-term audit storage
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
        timestamp=timestamp,
        correlated_risk_level=correlated_risk_level,
        correlation_reason=correlation_reason
    )