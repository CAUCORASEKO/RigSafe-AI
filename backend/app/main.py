from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
import uuid

app = FastAPI(
    title="RigSafe AI Backend",
    description="Safety signal ingestion backend for offshore oil & gas operations",
    version="0.1.0"
)

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
    message: str
    timestamp: datetime


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

    return SafetyResponse(
        status="accepted",
        signal_id=str(uuid.uuid4())[:8],
        risk_level=risk_level,
        severity_score=severity_score,
        message=message,
        timestamp=datetime.utcnow()
    )