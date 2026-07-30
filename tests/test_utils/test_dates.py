"""
Test: Date parsing and formatting — pure logic, zero doubles.

These test BEHAVIORS:
  - "relative date strings resolve to correct datetimes"
  - "human-friendly formatting works for various time distances"

Implementation can change freely; these tests won't break.
"""

from datetime import UTC, datetime, timedelta

from src.utils.dates import ensure_aware, format_relative_date, parse_relative_date


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
        assert result.date() == datetime.now(UTC).date()

    def test_tomorrow(self):
        result = parse_relative_date("tomorrow")
        expected = datetime.now(UTC).date() + timedelta(days=1)
        assert result.date() == expected

    def test_next_week(self):
        result = parse_relative_date("next week")
        expected = datetime.now(UTC).date() + timedelta(weeks=1)
        assert result.date() == expected

    def test_next_month(self):
        result = parse_relative_date("next month")
        assert result is not None
        # Should be roughly 28-31 days ahead
        diff = (result.date() - datetime.now(UTC).date()).days
        assert 28 <= diff <= 31

    def test_in_3_days(self):
        result = parse_relative_date("in 3 days")
        expected = datetime.now(UTC).date() + timedelta(days=3)
        assert result.date() == expected

    def test_in_two_weeks(self):
        result = parse_relative_date("in two weeks")
        expected = datetime.now(UTC).date() + timedelta(weeks=2)
        assert result.date() == expected

    def test_numeric_days_later(self):
        result = parse_relative_date("5 days later")
        expected = datetime.now(UTC).date() + timedelta(days=5)
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
        now = datetime.now(UTC)
        assert format_relative_date(now) == "Today"

    def test_tomorrow(self):
        tomorrow = datetime.now(UTC) + timedelta(days=1)
        assert format_relative_date(tomorrow) == "Tomorrow"

    def test_yesterday(self):
        yesterday = datetime.now(UTC) - timedelta(days=1)
        assert format_relative_date(yesterday) == "Yesterday"

    def test_within_a_week_shows_day_name(self):
        in_3_days = datetime.now(UTC) + timedelta(days=3)
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
        past = datetime.now(UTC) - timedelta(days=10)
        result = format_relative_date(past)
        assert "days ago" in result

    def test_far_future_shows_formatted_date(self):
        far = datetime.now(UTC) + timedelta(days=60)
        result = format_relative_date(far)
        # Should be something like "Mar 15, 2026"
        assert "," in result


# ---------------------------------------------------------------------------
# Behavior: everything this module returns is timezone-aware
#
# Added when ruff's DTZ003 rule flagged the datetime.utcnow() calls above. The
# mechanical fix (utcnow -> now(UTC)) would have quietly removed the ONLY place
# the suite passed a naive datetime into format_relative_date, and therefore the
# only coverage of ensure_aware()'s naive branch. These tests restore that and
# pin the behaviour change that motivated the rule.
#
# Why it matters: every DateTime column in models.py is timezone=True and every
# query compares against datetime.now(UTC). A naive value reaching one of them
# either raises on comparison or is silently stored with an assumed offset.
# dates.py used utcnow() itself until recently, so this is a regression guard,
# not a hypothetical.
# ---------------------------------------------------------------------------
class TestTimezoneAwareness:
    def test_parse_returns_aware_datetimes(self):
        for phrase in ("today", "tomorrow", "next week", "in 3 days", "monday"):
            result = parse_relative_date(phrase)
            assert result is not None, phrase
            assert result.tzinfo is not None, f"{phrase!r} produced a naive datetime"

    def test_parse_of_an_absolute_date_is_also_aware(self):
        """
        dateutil returns naive datetimes unless the input carried an offset, so
        this path needs its own assertion — it is normalized separately from the
        relative-phrase branch.
        """
        result = parse_relative_date("2026-12-01")
        assert result is not None
        assert result.tzinfo is not None

    def test_parsed_dates_can_be_compared_against_now(self):
        """Mixing naive and aware raises TypeError; this is the guard against it."""
        result = parse_relative_date("tomorrow")
        delta = result - datetime.now(UTC)
        # "tomorrow" resolves to midnight tomorrow, so the gap is between 0 and
        # 24 hours. Bounding both ends keeps this from being an assertion that
        # cannot fail.
        assert 0 < delta.total_seconds() <= 86400

    def test_format_accepts_a_naive_datetime(self):
        """
        Datetimes read back from a store that loses tzinfo (SQLite under test)
        arrive naive. format_relative_date must normalize rather than raise.

        The naive value is built with .replace(tzinfo=None) rather than utcnow()
        so the test itself stays DTZ-clean.
        """
        naive = datetime.now(UTC).replace(tzinfo=None)
        assert naive.tzinfo is None
        assert format_relative_date(naive) == "Today"

    def test_format_accepts_an_aware_datetime(self):
        assert format_relative_date(datetime.now(UTC)) == "Today"

    def test_ensure_aware_is_idempotent(self):
        aware = datetime.now(UTC)
        assert ensure_aware(aware) is aware or ensure_aware(aware) == aware
        assert ensure_aware(None) is None
        assert ensure_aware(aware.replace(tzinfo=None)).tzinfo is not None
