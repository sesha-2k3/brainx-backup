"""
Test: OCR service — two foreign system boundaries.

pytesseract shells out to the Tesseract binary → STUB it.
extract_contact_data calls the Groq API → STUB it.
_quick_extract is pure regex → test directly, no doubles.

Behaviors:
  - "_quick_extract finds emails, phones, urls via regex"
  - "process_business_card_bytes runs OCR + LLM extraction"
  - "process_business_card raises FileNotFoundError for missing files"
  - "regex fallback fills in fields LLM missed"
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.schemas.contacts import ExtractedContactData
from src.services.ocr import _quick_extract


# ---------------------------------------------------------------------------
# Pure logic: _quick_extract regex (zero doubles)
# ---------------------------------------------------------------------------
class TestQuickExtract:

    def test_extracts_email(self):
        text = "Jane Doe\njane@example.com\nAcme Corp"
        result = _quick_extract(text)
        assert result["email"] == "jane@example.com"

    def test_extracts_phone(self):
        text = "Call me at +1 (213) 373-4253"
        result = _quick_extract(text)
        assert "phone" in result
        assert "213" in result["phone"]

    def test_extracts_url(self):
        text = "Visit https://acme.com for more"
        result = _quick_extract(text)
        assert result["url"] == "https://acme.com"

    def test_empty_text_returns_empty(self):
        result = _quick_extract("No contact info here at all")
        assert "email" not in result

    def test_multiple_emails_takes_first(self):
        text = "alice@test.com and bob@test.com"
        result = _quick_extract(text)
        assert result["email"] == "alice@test.com"

    def test_email_lowercased(self):
        text = "Contact: ALICE@EXAMPLE.COM"
        result = _quick_extract(text)
        assert result["email"] == "alice@example.com"


# ---------------------------------------------------------------------------
# Foreign boundary: process_business_card_bytes (stubs pytesseract + Groq)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
class TestProcessBusinessCardBytes:

    @patch("src.services.ocr.extract_contact_data")
    @patch("src.services.ocr._run_ocr_sync")
    async def test_returns_extracted_data(self, mock_ocr_sync, mock_extract):
        # Stub OCR (pytesseract foreign boundary)
        mock_ocr_sync.return_value = (
            "Jane Doe\njane@example.com\nCTO at Acme Corp",
            0.85,
        )

        # Stub LLM extraction (Groq foreign boundary)
        mock_extract.return_value = ExtractedContactData(
            name="Jane Doe",
            email="jane@example.com",
            company="Acme Corp",
            role="CTO",
        )

        from src.services.ocr import process_business_card_bytes

        result = await process_business_card_bytes(b"fake-image-bytes")

        assert result["extracted"].name == "Jane Doe"
        assert result["confidence"] == 0.85
        assert "raw_text" in result

    @patch("src.services.ocr.extract_contact_data")
    @patch("src.services.ocr._run_ocr_sync")
    async def test_regex_fallback_fills_missing_email(self, mock_ocr_sync, mock_extract):
        # OCR finds email in raw text
        mock_ocr_sync.return_value = (
            "Bob Smith\nbob@company.com\n555-0100",
            0.90,
        )

        # But LLM misses the email
        mock_extract.return_value = ExtractedContactData(
            name="Bob Smith",
            email=None,  # LLM missed it
            company="SomeCo",
        )

        from src.services.ocr import process_business_card_bytes

        result = await process_business_card_bytes(b"fake-image")

        # Regex fallback should have filled in the email
        assert result["extracted"].email == "bob@company.com"

    @patch("src.services.ocr.extract_contact_data")
    @patch("src.services.ocr._run_ocr_sync")
    async def test_regex_fallback_fills_missing_phone(self, mock_ocr_sync, mock_extract):
        mock_ocr_sync.return_value = (
            "Carol White\n+12133734253",
            0.80,
        )

        mock_extract.return_value = ExtractedContactData(
            name="Carol White",
            phone=None,  # LLM missed it
        )

        from src.services.ocr import process_business_card_bytes

        result = await process_business_card_bytes(b"fake-image")
        assert result["extracted"].phone is not None


# ---------------------------------------------------------------------------
# Foreign boundary: process_business_card (file-based)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
class TestProcessBusinessCardFile:

    async def test_missing_file_raises(self):
        from src.services.ocr import process_business_card

        with pytest.raises(FileNotFoundError):
            await process_business_card("/nonexistent/card.png")
