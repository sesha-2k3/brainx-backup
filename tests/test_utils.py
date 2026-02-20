# Tests: Unit tests for utility functions

import pytest
from datetime import datetime, timedelta

from src.utils.phone import normalize_phone, format_phone_display
from src.utils.dates import parse_relative_date, format_relative_date
from src.utils.text import clean_text, truncate, normalize_name


class TestPhoneUtils:
    def test_normalize_phone_us(self):
        assert normalize_phone("(555) 123-4567") == "+15551234567"
        assert normalize_phone("555-123-4567") == "+15551234567"
        assert normalize_phone("5551234567") == "+15551234567"
    
    def test_normalize_phone_international(self):
        assert normalize_phone("+44 20 7946 0958") == "+442079460958"
    
    def test_normalize_phone_invalid(self):
        assert normalize_phone("123") is None
        assert normalize_phone("") is None
        assert normalize_phone(None) is None


class TestDateUtils:
    def test_parse_relative_today(self):
        result = parse_relative_date("today")
        assert result is not None
        assert result.date() == datetime.utcnow().date()
    
    def test_parse_relative_tomorrow(self):
        result = parse_relative_date("tomorrow")
        expected = datetime.utcnow().date() + timedelta(days=1)
        assert result is not None
        assert result.date() == expected
    
    def test_parse_relative_in_days(self):
        result = parse_relative_date("in 3 days")
        expected = datetime.utcnow().date() + timedelta(days=3)
        assert result is not None
        assert result.date() == expected
    
    def test_parse_absolute_date(self):
        result = parse_relative_date("2024-06-15")
        assert result is not None
        assert result.year == 2024
        assert result.month == 6
        assert result.day == 15
    
    def test_format_relative_today(self):
        today = datetime.utcnow()
        assert format_relative_date(today) == "Today"
    
    def test_format_relative_tomorrow(self):
        tomorrow = datetime.utcnow() + timedelta(days=1)
        assert format_relative_date(tomorrow) == "Tomorrow"


class TestTextUtils:
    def test_clean_text(self):
        assert clean_text("  hello   world  ") == "hello world"
        assert clean_text(None) == ""
    
    def test_truncate(self):
        text = "This is a long text that needs to be truncated"
        result = truncate(text, max_length=20)
        assert len(result) <= 20
        assert result.endswith("...")
    
    def test_truncate_short(self):
        text = "Short"
        assert truncate(text, max_length=20) == "Short"
    
    def test_normalize_name(self):
        assert normalize_name("john doe") == "John Doe"
        assert normalize_name("JANE SMITH") == "Jane Smith"
        assert normalize_name("o'brien") == "O'Brien"
        assert normalize_name("mcdonald") == "McDonald"
