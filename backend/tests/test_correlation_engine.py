"""
Comprehensive test suite for the correlation engine.

Tests the rule-based multi-signal correlation logic to ensure it is:
- Deterministic and predictable
- Safe for safety-critical environments
- Explainable and maintainable
"""

import pytest
from datetime import datetime, timedelta
from app.correlation import add_event, check_correlation, _location_windows


# Fixed base timestamp for deterministic tests
BASE_TIMESTAMP = datetime(2024, 1, 15, 10, 0, 0)


@pytest.fixture(autouse=True)
def reset_correlation_state():
    """
    Reset correlation engine state before each test.
    
    This ensures tests are isolated and deterministic by clearing
    the in-memory event windows between tests.
    """
    _location_windows.clear()
    yield
    _location_windows.clear()


class TestSingleEventNoCorrelation:
    """Test that single elevated events do not trigger correlation."""
    
    def test_single_elevated_gas_event_no_correlation(self):
        """
        Single elevated gas_concentration event should not trigger correlation.
        
        This test ensures that isolated events, even with elevated risk,
        do not incorrectly trigger correlation alarms. Safety systems must
        only alert when multiple correlated signals are present.
        """
        location = "compressor_module"
        timestamp = BASE_TIMESTAMP
        
        # Add single elevated gas event
        add_event(location, "gas_concentration", "elevated", timestamp)
        
        # Check correlation - should return None, None
        correlated_level, reason = check_correlation(
            location, "gas_concentration", "elevated", timestamp
        )
        
        assert correlated_level is None
        assert reason is None
    
    def test_single_high_gas_event_no_correlation(self):
        """
        Single high gas_concentration event should not trigger correlation.
        
        Even high-risk single events must not trigger correlation rules
        unless they are part of a correlated pattern.
        """
        location = "compressor_module"
        timestamp = BASE_TIMESTAMP
        
        add_event(location, "gas_concentration", "high", timestamp)
        
        correlated_level, reason = check_correlation(
            location, "gas_concentration", "high", timestamp
        )
        
        assert correlated_level is None
        assert reason is None
    
    def test_single_normal_event_no_correlation(self):
        """
        Normal risk events should not trigger correlation checks.
        
        The check_correlation function should return immediately for
        normal risk events without performing any correlation logic.
        """
        location = "compressor_module"
        timestamp = BASE_TIMESTAMP
        
        add_event(location, "gas_concentration", "normal", timestamp)
        
        correlated_level, reason = check_correlation(
            location, "gas_concentration", "normal", timestamp
        )
        
        assert correlated_level is None
        assert reason is None


class TestGasTemperatureCorrelation:
    """Test Rule 1: gas_concentration AND temperature correlation within 120 seconds."""
    
    def test_gas_and_temperature_elevated_within_120s_triggers_correlation(self):
        """
        Elevated gas_concentration and temperature within 120s should trigger high correlation.
        
        This is a critical safety rule: when both gas concentration and
        temperature are elevated in the same location within a short time
        window, it may indicate a developing hazardous situation.
        """
        location = "compressor_module"
        base_time = BASE_TIMESTAMP
        
        # Add gas event at t=0
        add_event(location, "gas_concentration", "elevated", base_time)
        
        # Add temperature event at t=60s (within 120s window)
        temp_time = base_time + timedelta(seconds=60)
        add_event(location, "temperature", "elevated", temp_time)
        
        # Check correlation on the temperature event
        correlated_level, reason = check_correlation(
            location, "temperature", "elevated", temp_time
        )
        
        assert correlated_level == "high"
        assert "gas_concentration and temperature" in reason.lower()
        assert "120 seconds" in reason.lower()
    
    def test_gas_and_temperature_high_within_120s_triggers_correlation(self):
        """
        High gas_concentration and high temperature within 120s should trigger correlation.
        
        Both signals at 'high' risk level must trigger the same correlation
        rule as elevated events, as they represent more severe conditions.
        """
        location = "compressor_module"
        base_time = BASE_TIMESTAMP
        
        add_event(location, "gas_concentration", "high", base_time)
        
        temp_time = base_time + timedelta(seconds=90)
        add_event(location, "temperature", "high", temp_time)
        
        correlated_level, reason = check_correlation(
            location, "temperature", "high", temp_time
        )
        
        assert correlated_level == "high"
        assert "gas_concentration and temperature" in reason.lower()
    
    def test_gas_elevated_temperature_high_mixed_triggers_correlation(self):
        """
        Mixed risk levels (elevated + high) should still trigger correlation.
        
        The rule applies to any combination of elevated/high levels,
        ensuring that different severity levels are still recognized
        as correlated risks.
        """
        location = "compressor_module"
        base_time = BASE_TIMESTAMP
        
        add_event(location, "gas_concentration", "elevated", base_time)
        
        temp_time = base_time + timedelta(seconds=50)
        add_event(location, "temperature", "high", temp_time)
        
        correlated_level, reason = check_correlation(
            location, "temperature", "high", temp_time
        )
        
        assert correlated_level == "high"
    
    def test_gas_and_temperature_outside_120s_no_correlation(self):
        """
        Gas and temperature events outside 120s window should not correlate.
        
        This ensures the time window constraint is properly enforced.
        Events more than 120 seconds apart should not trigger correlation,
        as they may represent unrelated incidents.
        """
        location = "compressor_module"
        base_time = BASE_TIMESTAMP
        
        add_event(location, "gas_concentration", "elevated", base_time)
        
        # Temperature event at t=121s (outside 120s window)
        temp_time = base_time + timedelta(seconds=121)
        add_event(location, "temperature", "elevated", temp_time)
        
        correlated_level, reason = check_correlation(
            location, "temperature", "elevated", temp_time
        )
        
        assert correlated_level is None
        assert reason is None
    
    def test_gas_and_temperature_different_locations_no_correlation(self):
        """
        Gas and temperature in different locations should not correlate.
        
        Correlation rules only apply within the same location, as risks
        are location-specific. Events in different locations are independent.
        """
        location1 = "compressor_module"
        location2 = "turbine_module"
        base_time = BASE_TIMESTAMP
        
        add_event(location1, "gas_concentration", "elevated", base_time)
        
        temp_time = base_time + timedelta(seconds=60)
        add_event(location2, "temperature", "elevated", temp_time)
        
        # Check correlation in location2 - should not find location1 events
        correlated_level, reason = check_correlation(
            location2, "temperature", "elevated", temp_time
        )
        
        assert correlated_level is None
        assert reason is None


class TestVibrationPressureCorrelation:
    """Test Rule 2: vibration AND pressure correlation within 120 seconds."""
    
    def test_vibration_and_pressure_elevated_within_120s_triggers_correlation(self):
        """
        Elevated vibration and pressure within 120s should trigger high correlation.
        
        This correlation rule detects mechanical stress patterns where
        vibration and pressure anomalies occur together, indicating
        potential equipment failure or operational issues.
        """
        location = "compressor_module"
        base_time = BASE_TIMESTAMP
        
        add_event(location, "vibration", "elevated", base_time)
        
        pressure_time = base_time + timedelta(seconds=80)
        add_event(location, "pressure", "elevated", pressure_time)
        
        correlated_level, reason = check_correlation(
            location, "pressure", "elevated", pressure_time
        )
        
        assert correlated_level == "high"
        assert "vibration and pressure" in reason.lower()
        assert "120 seconds" in reason.lower()
    
    def test_vibration_and_pressure_high_within_120s_triggers_correlation(self):
        """
        High vibration and high pressure within 120s should trigger correlation.
        
        Both signals at 'high' risk level represent severe mechanical
        stress conditions that require immediate attention.
        """
        location = "compressor_module"
        base_time = BASE_TIMESTAMP
        
        add_event(location, "vibration", "high", base_time)
        
        pressure_time = base_time + timedelta(seconds=100)
        add_event(location, "pressure", "high", pressure_time)
        
        correlated_level, reason = check_correlation(
            location, "pressure", "high", pressure_time
        )
        
        assert correlated_level == "high"
        assert "vibration and pressure" in reason.lower()
    
    def test_vibration_and_pressure_outside_120s_no_correlation(self):
        """
        Vibration and pressure events outside 120s window should not correlate.
        
        Time window enforcement ensures that only temporally related
        events trigger correlation, preventing false positives from
        unrelated incidents separated in time.
        """
        location = "compressor_module"
        base_time = BASE_TIMESTAMP
        
        add_event(location, "vibration", "elevated", base_time)
        
        # Pressure event at t=125s (outside 120s window)
        pressure_time = base_time + timedelta(seconds=125)
        add_event(location, "pressure", "elevated", pressure_time)
        
        correlated_level, reason = check_correlation(
            location, "pressure", "elevated", pressure_time
        )
        
        assert correlated_level is None
        assert reason is None


class TestMultipleEventsCorrelation:
    """Test Rule 3: Three or more elevated/high events within 180 seconds."""
    
    def test_three_elevated_events_within_180s_triggers_correlation(self):
        """
        Three or more elevated events within 180s should trigger high correlation.
        
        This rule detects patterns where multiple risk events occur
        rapidly in the same location, indicating a developing critical
        situation requiring immediate operator attention.
        """
        location = "compressor_module"
        base_time = BASE_TIMESTAMP
        
        # Add three elevated events within 180s window
        add_event(location, "gas_concentration", "elevated", base_time)
        add_event(location, "vibration", "elevated", base_time + timedelta(seconds=60))
        add_event(location, "temperature", "elevated", base_time + timedelta(seconds=120))
        
        # Check correlation on the third event
        check_time = base_time + timedelta(seconds=120)
        correlated_level, reason = check_correlation(
            location, "temperature", "elevated", check_time
        )
        
        assert correlated_level == "high"
        assert "3" in reason or "three" in reason.lower()
        assert "180 seconds" in reason.lower()
    
    def test_three_high_events_within_180s_triggers_correlation(self):
        """
        Three high-risk events within 180s should trigger correlation.
        
        All events at 'high' risk level represent a critical situation
        where multiple severe conditions are present simultaneously.
        """
        location = "compressor_module"
        base_time = BASE_TIMESTAMP
        
        add_event(location, "gas_concentration", "high", base_time)
        add_event(location, "pressure", "high", base_time + timedelta(seconds=90))
        add_event(location, "temperature", "high", base_time + timedelta(seconds=150))
        
        check_time = base_time + timedelta(seconds=150)
        correlated_level, reason = check_correlation(
            location, "temperature", "high", check_time
        )
        
        assert correlated_level == "high"
        assert "3" in reason or "three" in reason.lower()
    
    def test_mixed_elevated_and_high_events_within_180s_triggers_correlation(self):
        """
        Mixed elevated and high events should count toward the 3+ event rule.
        
        Any combination of elevated/high risk levels should be counted,
        as they all represent non-normal operating conditions requiring attention.
        """
        location = "compressor_module"
        base_time = BASE_TIMESTAMP
        
        add_event(location, "gas_concentration", "elevated", base_time)
        add_event(location, "vibration", "high", base_time + timedelta(seconds=70))
        add_event(location, "temperature", "elevated", base_time + timedelta(seconds=140))
        
        check_time = base_time + timedelta(seconds=140)
        correlated_level, reason = check_correlation(
            location, "temperature", "elevated", check_time
        )
        
        assert correlated_level == "high"
    
    def test_four_events_within_180s_triggers_correlation(self):
        """
        Four or more events within 180s should trigger correlation.
        
        This test ensures that the rule correctly handles cases with
        more than the minimum threshold of 3 events.
        """
        location = "compressor_module"
        base_time = BASE_TIMESTAMP
        
        add_event(location, "gas_concentration", "elevated", base_time)
        add_event(location, "vibration", "elevated", base_time + timedelta(seconds=45))
        add_event(location, "temperature", "elevated", base_time + timedelta(seconds=90))
        add_event(location, "pressure", "elevated", base_time + timedelta(seconds=135))
        
        check_time = base_time + timedelta(seconds=135)
        correlated_level, reason = check_correlation(
            location, "pressure", "elevated", check_time
        )
        
        assert correlated_level == "high"
        assert "4" in reason or "four" in reason.lower()
    
    def test_three_events_outside_180s_window_no_correlation(self):
        """
        Three events outside 180s window span should not trigger correlation.
        
        Events that are spread over more than 180 seconds should not
        trigger the multi-event correlation rule, even if there are 3 or more.
        """
        location = "compressor_module"
        base_time = BASE_TIMESTAMP
        
        add_event(location, "gas_concentration", "elevated", base_time)
        add_event(location, "vibration", "elevated", base_time + timedelta(seconds=90))
        # Third event at t=181s (outside 180s window from first event)
        add_event(location, "temperature", "elevated", base_time + timedelta(seconds=181))
        
        check_time = base_time + timedelta(seconds=181)
        correlated_level, reason = check_correlation(
            location, "temperature", "elevated", check_time
        )
        
        assert correlated_level is None
        assert reason is None
    
    def test_two_events_within_180s_no_correlation(self):
        """
        Only two elevated/high events should not trigger Rule 3 correlation.
        
        The threshold is explicitly set at 3 or more events. Two events
        alone should not trigger the multi-event correlation rule.
        """
        location = "compressor_module"
        base_time = BASE_TIMESTAMP
        
        add_event(location, "gas_concentration", "elevated", base_time)
        add_event(location, "vibration", "elevated", base_time + timedelta(seconds=100))
        
        check_time = base_time + timedelta(seconds=100)
        correlated_level, reason = check_correlation(
            location, "vibration", "elevated", check_time
        )
        
        assert correlated_level is None
        assert reason is None


class TestNormalEventsExclusion:
    """Test that normal risk events do not contribute to correlation."""
    
    def test_normal_events_do_not_count_toward_three_event_rule(self):
        """
        Normal risk events must not contribute to the 3+ event correlation rule.
        
        Only elevated/high risk events should be counted. Normal events
        represent acceptable operating conditions and should not trigger
        correlation alarms, even if they occur frequently.
        """
        location = "compressor_module"
        base_time = BASE_TIMESTAMP
        
        # Add two elevated events and multiple normal events
        add_event(location, "gas_concentration", "elevated", base_time)
        add_event(location, "vibration", "normal", base_time + timedelta(seconds=30))
        add_event(location, "temperature", "normal", base_time + timedelta(seconds=60))
        add_event(location, "pressure", "elevated", base_time + timedelta(seconds=90))
        add_event(location, "gas_concentration", "normal", base_time + timedelta(seconds=120))
        
        # Only 2 elevated events, should not trigger correlation
        check_time = base_time + timedelta(seconds=120)
        correlated_level, reason = check_correlation(
            location, "gas_concentration", "normal", check_time
        )
        
        # Normal event should not even be checked
        assert correlated_level is None
        assert reason is None
    
    def test_normal_events_do_not_trigger_gas_temperature_rule(self):
        """
        Normal gas or temperature events should not trigger Rule 1 correlation.
        
        Rule 1 specifically requires elevated/high levels for both
        gas_concentration and temperature. Normal levels should not
        participate in this correlation check.
        """
        location = "compressor_module"
        base_time = BASE_TIMESTAMP
        
        add_event(location, "gas_concentration", "normal", base_time)
        add_event(location, "temperature", "elevated", base_time + timedelta(seconds=60))
        
        check_time = base_time + timedelta(seconds=60)
        correlated_level, reason = check_correlation(
            location, "temperature", "elevated", check_time
        )
        
        assert correlated_level is None
        assert reason is None
    
    def test_mixed_normal_and_elevated_does_not_trigger_binary_rules(self):
        """
        Binary correlation rules require both signals to be elevated/high.
        
        Rules 1 and 2 require both signal types to be at elevated/high
        risk levels. Normal risk in either signal should prevent correlation.
        """
        location = "compressor_module"
        base_time = BASE_TIMESTAMP
        
        # Gas elevated, but temperature normal
        add_event(location, "gas_concentration", "elevated", base_time)
        add_event(location, "temperature", "normal", base_time + timedelta(seconds=60))
        
        check_time = base_time + timedelta(seconds=60)
        correlated_level, reason = check_correlation(
            location, "temperature", "normal", check_time
        )
        
        # Normal event should not trigger check, but even if it did,
        # temperature is normal so correlation should not occur
        assert correlated_level is None
        assert reason is None


class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_exactly_120_seconds_boundary_triggers_correlation(self):
        """
        Events exactly 120 seconds apart should trigger correlation.
        
        Boundary condition test: events at exactly the time window
        boundary (120s) should be included in the correlation check.
        """
        location = "compressor_module"
        base_time = BASE_TIMESTAMP
        
        add_event(location, "gas_concentration", "elevated", base_time)
        
        # Temperature event exactly 120s later
        temp_time = base_time + timedelta(seconds=120)
        add_event(location, "temperature", "elevated", temp_time)
        
        correlated_level, reason = check_correlation(
            location, "temperature", "elevated", temp_time
        )
        
        # Should trigger correlation (events are within 120s window)
        assert correlated_level == "high"
    
    def test_exactly_180_seconds_boundary_for_three_events(self):
        """
        Three events spanning exactly 180 seconds should trigger correlation.
        
        Boundary condition test: events that span exactly the 180s
        window should trigger the multi-event correlation rule.
        """
        location = "compressor_module"
        base_time = BASE_TIMESTAMP
        
        add_event(location, "gas_concentration", "elevated", base_time)
        add_event(location, "vibration", "elevated", base_time + timedelta(seconds=90))
        # Third event exactly 180s after first
        add_event(location, "temperature", "elevated", base_time + timedelta(seconds=180))
        
        check_time = base_time + timedelta(seconds=180)
        correlated_level, reason = check_correlation(
            location, "temperature", "elevated", check_time
        )
        
        assert correlated_level == "high"
    
    def test_empty_location_returns_no_correlation(self):
        """
        Checking correlation for an empty location should return None.
        
        Locations without any events should not trigger any correlation,
        regardless of the signal type or risk level being checked.
        """
        location = "empty_module"
        timestamp = BASE_TIMESTAMP
        
        # No events added for this location
        correlated_level, reason = check_correlation(
            location, "gas_concentration", "elevated", timestamp
        )
        
        assert correlated_level is None
        assert reason is None
    
    def test_no_location_returns_no_correlation(self):
        """
        Events without location should not trigger correlation checks.
        
        The add_event function skips events without location, and
        check_correlation should return None for empty location strings.
        """
        location = ""  # Empty location
        timestamp = BASE_TIMESTAMP
        
        # Event without location is not added
        add_event(location, "gas_concentration", "elevated", timestamp)
        
        correlated_level, reason = check_correlation(
            location, "gas_concentration", "elevated", timestamp
        )
        
        assert correlated_level is None
        assert reason is None
    
    def test_rule_priority_gas_temperature_takes_precedence(self):
        """
        Rule 1 (gas/temperature) should be checked before Rule 3 (3+ events).
        
        When multiple rules could apply, Rule 1 should be detected first.
        This test ensures rule evaluation order is correct.
        """
        location = "compressor_module"
        base_time = BASE_TIMESTAMP
        
        # Setup that could match both Rule 1 and Rule 3
        add_event(location, "gas_concentration", "elevated", base_time)
        add_event(location, "temperature", "elevated", base_time + timedelta(seconds=60))
        add_event(location, "vibration", "elevated", base_time + timedelta(seconds=90))
        
        check_time = base_time + timedelta(seconds=90)
        correlated_level, reason = check_correlation(
            location, "vibration", "elevated", check_time
        )
        
        # Should trigger Rule 1 (gas/temperature) correlation
        assert correlated_level == "high"
        assert "gas_concentration and temperature" in reason.lower()
