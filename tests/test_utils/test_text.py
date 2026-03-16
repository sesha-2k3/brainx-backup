"""
Test: Text processing utilities — pure logic, zero doubles.

Behaviors:
  - "text cleaning normalizes whitespace and strips edges"
  - "truncation preserves word boundaries"
  - "name normalization handles edge cases (Mc/Mac prefixes)"
  - "LIKE escaping prevents SQL injection patterns"
  - "LLM JSON parsing handles markdown code blocks"
"""

import pytest

from src.utils.text import (
    build_search_text,
    clean_text,
    escape_like,
    extract_emails,
    extract_urls,
    normalize_name,
    parse_llm_json,
    truncate,
)


class TestCleanText:
    def test_none_returns_empty(self):
        assert clean_text(None) == ""

    def test_collapses_whitespace(self):
        assert clean_text("hello   world") == "hello world"

    def test_strips_edges(self):
        assert clean_text("  hello  ") == "hello"

    def test_normalizes_newlines_and_tabs(self):
        assert clean_text("hello\n\tworld") == "hello world"


class TestTruncate:
    def test_none_returns_empty(self):
        assert truncate(None) == ""

    def test_short_text_unchanged(self):
        assert truncate("hello", max_length=200) == "hello"

    def test_long_text_truncated_at_word_boundary(self):
        text = "the quick brown fox jumps over the lazy dog"
        result = truncate(text, max_length=20)
        assert len(result) <= 20
        assert result.endswith("...")

    def test_custom_suffix(self):
        result = truncate("a very long string indeed", max_length=15, suffix="…")
        assert result.endswith("…")


class TestNormalizeName:
    def test_none_returns_empty(self):
        assert normalize_name(None) == ""

    def test_title_case(self):
        assert normalize_name("john doe") == "John Doe"

    def test_mcdonald(self):
        assert normalize_name("ronald mcdonald") == "Ronald McDonald"

    def test_macdonald(self):
        assert normalize_name("angus macdonald") == "Angus MacDonald"

    def test_extra_whitespace(self):
        assert normalize_name("  jane   doe  ") == "Jane Doe"


class TestExtractEmails:
    def test_finds_emails(self):
        text = "Contact us at hello@example.com or info@test.org"
        emails = extract_emails(text)
        assert "hello@example.com" in emails
        assert "info@test.org" in emails

    def test_no_emails(self):
        assert extract_emails("no emails here") == []


class TestExtractUrls:
    def test_finds_urls(self):
        text = "Visit https://example.com or http://test.org/page"
        urls = extract_urls(text)
        assert len(urls) == 2

    def test_no_urls(self):
        assert extract_urls("no urls here") == []


class TestEscapeLike:
    """Prevent LIKE pattern injection."""

    def test_escapes_percent(self):
        assert escape_like("100%") == "100\\%"

    def test_escapes_underscore(self):
        assert escape_like("user_name") == "user\\_name"

    def test_escapes_backslash(self):
        assert escape_like("a\\b") == "a\\\\b"

    def test_normal_text_unchanged(self):
        assert escape_like("hello world") == "hello world"

    def test_combined(self):
        assert escape_like("50%_off\\sale") == "50\\%\\_off\\\\sale"


class TestBuildSearchText:
    def test_combines_fields(self):
        result = build_search_text("John Doe", "john@example.com", "Acme")
        assert "john doe" in result
        assert "john@example.com" in result
        assert "acme" in result

    def test_skips_none(self):
        result = build_search_text("John", None, "Acme")
        assert result == "john acme"


class TestParseLlmJson:
    def test_raw_json(self):
        result = parse_llm_json('{"name": "Jane"}')
        assert result["name"] == "Jane"

    def test_markdown_code_block(self):
        content = '```json\n{"name": "Jane"}\n```'
        result = parse_llm_json(content)
        assert result["name"] == "Jane"

    def test_markdown_without_language(self):
        content = '```\n{"name": "Jane"}\n```'
        result = parse_llm_json(content)
        assert result["name"] == "Jane"

    def test_invalid_json_raises(self):
        with pytest.raises(Exception):
            parse_llm_json("not json at all")
