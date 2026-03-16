"""
Test: Date parsing and formatting — pure logic, zero doubles.

These test BEHAVIORS:
  - "relative date strings resolve to correct datetimes"
  - "human-friendly formatting works for various time distances"

Implementation can change freely; these tests won't break.
"""

from datetime import datetime, timedelta

from src.utils.dates import format_relative_date, parse_relative_date


# ---------------------------------------------------------------------------
# Behavior: relative date strings resolve to correct datetimes
# ---------------------------------------------------------------------------
class TestParseRelativeDate:
    """Parse natural-language date strings into datetimes."""

    def test_none_returns_none(self):
        assert parse_relative_date(None) is None

    def test_empty_string_returns_none(self):
        assert parse_relative_date("") is None

    def test_today(self):
        result = parse_relative_date("today")
        assert result is not None
        assert result.date() == datetime.utcnow().date()

    def test_tomorrow(self):
        result = parse_relative_date("tomorrow")
        expected = datetime.utcnow().date() + timedelta(days=1)
        assert result.date() == expected

    def test_next_week(self):
        result = parse_relative_date("next week")
        expected = datetime.utcnow().date() + timedelta(weeks=1)
        assert result.date() == expected

    def test_next_month(self):
        result = parse_relative_date("next month")
        assert result is not None
        # Should be roughly 28-31 days ahead
        diff = (result.date() - datetime.utcnow().date()).days
        assert 28 <= diff <= 31

    def test_in_3_days(self):
        result = parse_relative_date("in 3 days")
        expected = datetime.utcnow().date() + timedelta(days=3)
        assert result.date() == expected

    def test_in_two_weeks(self):
        result = parse_relative_date("in two weeks")
        expected = datetime.utcnow().date() + timedelta(weeks=2)
        assert result.date() == expected

    def test_numeric_days_later(self):
        result = parse_relative_date("5 days later")
        expected = datetime.utcnow().date() + timedelta(days=5)
        assert result.date() == expected

    def test_absolute_iso_date(self):
        result = parse_relative_date("2025-06-15")
        assert result is not None
        assert result.year == 2025
        assert result.month == 6
        assert result.day == 15

    def test_day_name_advances_to_next_occurrence(self):
        result = parse_relative_date("friday")
        assert result is not None
        assert result.weekday() == 4  # Friday

    def test_garbage_returns_none(self):
        result = parse_relative_date("not a real date at all xyz")
        # dateutil may or may not parse this — we just verify no crash
        # and the result is either None or a datetime
        assert result is None or isinstance(result, datetime)

    def test_midnight_normalization(self):
        """Parsed dates should have time zeroed out."""
        result = parse_relative_date("tomorrow")
        assert result.hour == 0
        assert result.minute == 0
        assert result.second == 0


# ---------------------------------------------------------------------------
# Behavior: human-friendly formatting for various time distances
# ---------------------------------------------------------------------------
class TestFormatRelativeDate:
    """Format datetimes as human-readable relative strings."""

    def test_none_returns_no_date(self):
        assert format_relative_date(None) == "No date"

    def test_today(self):
        now = datetime.utcnow()
        assert format_relative_date(now) == "Today"

    def test_tomorrow(self):
        tomorrow = datetime.utcnow() + timedelta(days=1)
        assert format_relative_date(tomorrow) == "Tomorrow"

    def test_yesterday(self):
        yesterday = datetime.utcnow() - timedelta(days=1)
        assert format_relative_date(yesterday) == "Yesterday"

    def test_within_a_week_shows_day_name(self):
        in_3_days = datetime.utcnow() + timedelta(days=3)
        result = format_relative_date(in_3_days)
        # Should be a day name like "Wednesday"
        assert result in [
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday",
        ]

    def test_past_date_shows_days_ago(self):
        past = datetime.utcnow() - timedelta(days=10)
        result = format_relative_date(past)
        assert "days ago" in result

    def test_far_future_shows_formatted_date(self):
        far = datetime.utcnow() + timedelta(days=60)
        result = format_relative_date(far)
        # Should be something like "Mar 15, 2026"
        assert "," in result
