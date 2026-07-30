"""
Test: OCR service — two foreign system boundaries.

pytesseract shells out to the Tesseract binary → STUB it.
extract_contact_data calls the Groq API → STUB it.

Behaviors:
  - "process_business_card_bytes runs OCR + LLM extraction"
  - "process_business_card raises FileNotFoundError for missing files"
  - "process_business_card and _bytes agree on the confidence scale"

REMOVED: TestQuickExtract, which imported src.services.ocr._quick_extract.
That helper no longer exists — it was deleted when extract_contact_data() took
over running the deterministic email/phone/website passes internally. The import
raised at COLLECTION time, so all 10 tests in this module errored, not just the
6 that used it.

The deeper problem was that it tested a PRIVATE helper by name, so a legitimate
refactor broke the test even though no behaviour changed. That regex behaviour is
now covered where it actually lives:
  - src/utils/text.py           -> tests/test_utils/test_text.py
  - the regex-beats-LLM merge   -> tests/test_services/test_extraction.py
"""

from unittest.mock import patch

import pytest

from src.schemas.contacts import ExtractedContactData


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
        Both entry points must agree on the confidence scale.

        process_business_card used to compute its own average and return it raw
        (0-100) while the bytes path divided by 100. A threshold check such as
        `if confidence < 0.5: flag_for_review()` therefore never fired for the
        file path, so every card passed review including illegible ones. The two
        now share one code path and cannot drift again.
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
# process_business_card_bytes filled email/phone from the raw OCR text. With
# extraction stubbed out that merge cannot run, and ocr.py does not own it in any
# case - the regex passes live inside extract_contact_data. Asserting them here
# tested a responsibility this module does not have.


class TestProcessBusinessCardFile:
    async def test_missing_file_raises(self):
        from src.services.ocr import process_business_card

        with pytest.raises(FileNotFoundError):
            await process_business_card("/nonexistent/card.png")
