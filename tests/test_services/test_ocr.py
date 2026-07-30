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

from unittest.mock import patch

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
    async def test_confidence_is_a_zero_to_one_fraction(self, mock_ocr_sync, mock_extract):
        """
        The two entry points must agree on the confidence scale.

        process_business_card used to compute its own average and return it raw
        (0-100) while the bytes path divided by 100, so a threshold check like
        `if confidence < 0.5` never fired for the file path and every card passed
        review, including illegible ones. Both now share one code path.
        """
        mock_ocr_sync.return_value = ("Some Card Text", 0.42)
        mock_extract.return_value = ExtractedContactData(name="Someone")

        from src.services.ocr import process_business_card_bytes

        result = await process_business_card_bytes(b"fake-image-bytes")

        assert 0.0 <= result["confidence"] <= 1.0
        assert result["confidence"] == 0.42


# NOTE: test_regex_fallback_fills_missing_email and
# test_regex_fallback_fills_missing_phone moved to
# tests/test_services/test_extraction.py.
#
# Both patched src.services.ocr.extract_contact_data and then asserted that
# process_business_card_bytes filled in email/phone from the raw OCR text. With
# extraction stubbed out that merge cannot run, and ocr.py does not own it
# anyway - the regex passes live inside extract_contact_data. Asserting them
# here tested a responsibility this module does not have.


class TestProcessBusinessCardFile:
    async def test_missing_file_raises(self):
        from src.services.ocr import process_business_card

        with pytest.raises(FileNotFoundError):
            await process_business_card("/nonexistent/card.png")
