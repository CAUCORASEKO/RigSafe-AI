"""
Multi-signal correlation engine for RigSafe-AI.

Implements explainable, rule-based correlation detection using sliding windows
to identify correlated safety events that may indicate higher risk situations.
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
from collections import defaultdict, deque


# Configuration constants
MAX_EVENTS_PER_LOCATION = 50
MAX_WINDOW_AGE_SECONDS = 300


class EventWindow:
    """In-memory sliding window for events within a location."""
    
    def __init__(self, max_events: int = MAX_EVENTS_PER_LOCATION, 
                 max_age_seconds: int = MAX_WINDOW_AGE_SECONDS):
        self.max_events = max_events
        self.max_age_seconds = max_age_seconds
        self.events: deque = deque(maxlen=max_events)
    
    def add_event(self, signal_type: str, risk_level: str, timestamp: datetime) -> None:
        """Add an event to the window and prune old events."""
        # Prune events older than max_age_seconds
        cutoff_time = timestamp - timedelta(seconds=self.max_age_seconds)
        while self.events and self.events[0]["timestamp"] < cutoff_time:
            self.events.popleft()
        
        # Add new event
        self.events.append({
            "signal_type": signal_type,
            "risk_level": risk_level,
            "timestamp": timestamp
        })
    
    def get_recent_events(self, within_seconds: int, timestamp: datetime) -> List[Dict]:
        """Get events within the specified time window."""
        cutoff_time = timestamp - timedelta(seconds=within_seconds)
        return [
            event for event in self.events
            if event["timestamp"] >= cutoff_time
        ]


# Global in-memory storage: location -> EventWindow
_location_windows: Dict[str, EventWindow] = defaultdict(
    lambda: EventWindow(MAX_EVENTS_PER_LOCATION, MAX_WINDOW_AGE_SECONDS)
)


def add_event(location: str, signal_type: str, risk_level: str, timestamp: datetime) -> None:
    """
    Add an event to the sliding window for the specified location.
    
    Args:
        location: Location identifier (e.g., "compressor_module")
        signal_type: Type of signal (e.g., "gas_concentration", "temperature")
        risk_level: Risk level of the signal ("normal", "elevated", "high")
        timestamp: Event timestamp
    """
    if not location:
        return  # Skip events without location
    
    window = _location_windows[location]
    window.add_event(signal_type, risk_level, timestamp)


def check_correlation(
    location: str, 
    signal_type: str, 
    risk_level: str, 
    timestamp: datetime
) -> Tuple[Optional[str], Optional[str]]:
    """
    Check for correlated risk patterns based on explainable rules.
    
    Note: The current event should already be added to the window via add_event()
    before calling this function, so it will be included in the correlation checks.
    
    Args:
        location: Location identifier
        signal_type: Type of the current signal
        risk_level: Risk level of the current signal
        timestamp: Current event timestamp
    
    Returns:
        Tuple of (correlated_risk_level, correlation_reason) or (None, None) if no correlation
    """
    if not location or risk_level not in ["elevated", "high"]:
        return None, None
    
    window = _location_windows.get(location)
    if not window:
        return None, None
    
    # Get recent events including the one we just added
    recent_events = window.get_recent_events(180, timestamp)  # Max window for all rules
    
    # Filter elevated/high events for efficiency
    elevated_high_events = [
        e for e in recent_events 
        if e["risk_level"] in ["elevated", "high"]
    ]
    
    # Rule 1: gas_concentration (elevated/high) AND temperature (elevated/high) within 120s
    events_120s = window.get_recent_events(120, timestamp)
    gas_events_120s = [e for e in events_120s
                      if e["signal_type"] == "gas_concentration" 
                      and e["risk_level"] in ["elevated", "high"]]
    temp_events_120s = [e for e in events_120s
                       if e["signal_type"] == "temperature" 
                       and e["risk_level"] in ["elevated", "high"]]
    
    # If both types exist in the 120s window, they're within 120s of each other
    if gas_events_120s and temp_events_120s:
        return "high", "Correlated high risk: elevated/high gas_concentration and temperature detected within 120 seconds in same location"
    
    # Rule 2: vibration (elevated/high) AND pressure (elevated/high) within 120s
    vib_events_120s = [e for e in events_120s
                      if e["signal_type"] == "vibration" 
                      and e["risk_level"] in ["elevated", "high"]]
    pressure_events_120s = [e for e in events_120s
                           if e["signal_type"] == "pressure" 
                           and e["risk_level"] in ["elevated", "high"]]
    
    # If both types exist in the 120s window, they're within 120s of each other
    if vib_events_120s and pressure_events_120s:
        return "high", "Correlated high risk: elevated/high vibration and pressure detected within 120 seconds in same location"
    
    # Rule 3: >=3 elevated/high events of any type within 180s
    if len(elevated_high_events) >= 3:
        # Verify all events are within 180s window of each other
        event_times = [e["timestamp"] for e in elevated_high_events]
        min_time = min(event_times)
        max_time = max(event_times)
        window_span = (max_time - min_time).total_seconds()
        
        if window_span <= 180:
            return "high", f"Correlated high risk: {len(elevated_high_events)} elevated/high events detected within 180 seconds in same location"
    
    return None, None


def get_involved_signal_types(
    location: str,
    timestamp: datetime
) -> List[str]:
    """
    Get unique signal types involved in correlated events for a location.
    
    This function extracts the signal types from elevated/high events
    within the correlation window, used for persistence and audit trails.
    
    Args:
        location: Location identifier
        timestamp: Reference timestamp for correlation window
    
    Returns:
        List of unique signal types involved in correlated events
    """
    if not location:
        return []
    
    window = _location_windows.get(location)
    if not window:
        return []
    
    # Get elevated/high events from the correlation window (180s)
    recent_events = window.get_recent_events(180, timestamp)
    elevated_high_events = [
        e for e in recent_events
        if e["risk_level"] in ["elevated", "high"]
    ]
    
    # Extract unique signal types
    signal_types = {event["signal_type"] for event in elevated_high_events}
    return sorted(list(signal_types))
