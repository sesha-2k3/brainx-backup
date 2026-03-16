"""
Test: Phone number normalization — pure logic, zero doubles.

Behaviors tested:
  - "valid US numbers normalize to E.164 format"
  - "invalid/missing input returns None gracefully"
  - "display formatting produces human-readable output"
"""

from src.utils.phone import format_phone_display, normalize_phone


class TestNormalizePhone:
    """Normalize various phone formats to E.164."""

    def test_none_returns_none(self):
        assert normalize_phone(None) is None

    def test_empty_string_returns_none(self):
        assert normalize_phone("") is None

    def test_standard_us_number(self):
        # Use a valid US number format (555 is fictional and fails validation)
        result = normalize_phone("(213) 373-4253")
        assert result is not None
        assert result.startswith("+1")

    def test_us_number_with_country_code(self):
        result = normalize_phone("+1-213-373-4253")
        assert result == "+12133734253"

    def test_fictional_number_falls_back_to_digits(self):
        # 555 numbers aren't valid — phonenumbers rejects them,
        # but the fallback returns cleaned digits (10+ chars)
        result = normalize_phone("5551234567")
        assert result is not None
        assert "5551234567" in result

    def test_international_format(self):
        result = normalize_phone("+44 20 7946 0958", default_region="GB")
        assert result is not None
        assert result.startswith("+44")

    def test_short_number_returns_none(self):
        """Numbers too short to be valid should return None."""
        result = normalize_phone("12345")
        assert result is None

    def test_with_dots_and_spaces(self):
        result = normalize_phone("213.373.4253")
        assert result is not None


class TestFormatPhoneDisplay:
    """Format phone numbers for human display."""

    def test_none_returns_none(self):
        assert format_phone_display(None) is None

    def test_e164_formats_to_national(self):
        result = format_phone_display("+15551234567")
        assert result is not None
        # Should be something like "(555) 123-4567"
        assert "555" in result

    def test_invalid_passes_through(self):
        result = format_phone_display("not-a-phone")
        assert result == "not-a-phone"
