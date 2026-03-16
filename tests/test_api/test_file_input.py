"""
Test: File upload input processing via HTTP API.

The /api/input/file endpoint calls three foreign systems:
  - Groq Whisper (transcription)
  - Tesseract (OCR)
  - Groq LLM (extraction)
All three are stubbed.

Behaviors:
  - "POST /api/input/file with audio transcribes and creates proposal"
  - "POST /api/input/file with image runs OCR and creates proposal"
  - "POST /api/input/file rejects unsupported content types"
  - "POST /api/input/file rejects oversized files"
"""

from unittest.mock import patch

import pytest

from src.schemas.contacts import ExtractedContactData


@pytest.mark.asyncio
class TestFileInputAudio:
    @patch("src.api.web.extract_contact_data")
    @patch("src.api.web.transcribe_audio_bytes")
    async def test_audio_upload_creates_proposal(self, mock_transcribe, mock_extract, client):
        mock_transcribe.return_value = {
            "text": "Met Sarah from BigCorp, she is the VP of Sales",
            "duration": 10.0,
            "language": "en",
        }
        mock_extract.return_value = ExtractedContactData(
            name="Sarah",
            company="BigCorp",
            role="VP of Sales",
            category="client",
            interaction_summary="Initial meeting",
            tasks=[],
        )

        resp = await client.post(
            "/api/input/file",
            files={"file": ("voice.ogg", b"fake-audio-bytes", "audio/ogg")},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "id" in body
        assert body["extracted_data"]["name"] == "Sarah"

    @patch("src.api.web.extract_contact_data")
    @patch("src.api.web.transcribe_audio_bytes")
    async def test_audio_no_name_returns_400(self, mock_transcribe, mock_extract, client):
        mock_transcribe.return_value = {"text": "some noise", "duration": 2.0}
        mock_extract.return_value = ExtractedContactData(name=None)

        resp = await client.post(
            "/api/input/file",
            files={"file": ("noise.ogg", b"noise", "audio/ogg")},
        )
        assert resp.status_code == 400


@pytest.mark.asyncio
class TestFileInputImage:
    @patch("src.api.web.find_duplicate")
    @patch("src.api.web.process_business_card_bytes")
    async def test_image_upload_creates_proposal(self, mock_ocr, mock_dedup, client):
        mock_ocr.return_value = {
            "raw_text": "Jane Doe\njane@example.com",
            "confidence": 0.92,
            "extracted": ExtractedContactData(
                name="Jane Doe",
                email="jane@example.com",
                company="TestCo",
            ),
        }
        mock_dedup.return_value = None  # No duplicate

        resp = await client.post(
            "/api/input/file",
            files={"file": ("card.jpg", b"fake-image-bytes", "image/jpeg")},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["extracted_data"]["name"] == "Jane Doe"
        assert body["confidence_score"] == 0.92

    @patch("src.api.web.process_business_card_bytes")
    async def test_image_no_name_returns_400(self, mock_ocr, client):
        mock_ocr.return_value = {
            "raw_text": "blurry text",
            "confidence": 0.3,
            "extracted": ExtractedContactData(name=None),
        }

        resp = await client.post(
            "/api/input/file",
            files={"file": ("bad.jpg", b"blurry", "image/jpeg")},
        )
        assert resp.status_code == 400


@pytest.mark.asyncio
class TestFileInputValidation:
    async def test_unsupported_content_type_rejected(self, client):
        resp = await client.post(
            "/api/input/file",
            files={"file": ("doc.pdf", b"pdf-content", "application/pdf")},
        )
        assert resp.status_code == 400
        assert "Unsupported" in resp.json()["detail"]
