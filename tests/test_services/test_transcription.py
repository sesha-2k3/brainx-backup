"""
Test: Audio transcription service — foreign system boundary.

Stubs the Groq Whisper API. Tests behaviors:
  - "transcribe_audio_bytes returns text, duration, language from Groq"
  - "transcribe_audio raises FileNotFoundError for missing files"
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.transcription import transcribe_audio, transcribe_audio_bytes


def _make_whisper_response(text="Hello world", duration=5.0, language="en"):
    """Build a canned Groq Whisper transcription response."""
    resp = MagicMock()
    resp.text = text
    resp.duration = duration
    resp.language = language
    return resp


@pytest.mark.asyncio
class TestTranscribeAudioBytes:
    @patch("src.services.transcription.get_groq_client")
    async def test_returns_text_and_metadata(self, mock_get_client):
        client = AsyncMock()
        client.audio.transcriptions.create = AsyncMock(
            return_value=_make_whisper_response(
                text="Met John from Acme Corp",
                duration=12.5,
                language="en",
            )
        )
        mock_get_client.return_value = client

        result = await transcribe_audio_bytes(b"fake-audio-bytes", "test.ogg")

        assert result["text"] == "Met John from Acme Corp"
        assert result["duration"] == 12.5
        assert result["language"] == "en"

    @patch("src.services.transcription.get_groq_client")
    async def test_default_filename(self, mock_get_client):
        client = AsyncMock()
        client.audio.transcriptions.create = AsyncMock(
            return_value=_make_whisper_response(text="Some audio")
        )
        mock_get_client.return_value = client

        result = await transcribe_audio_bytes(b"fake-bytes")
        assert result["text"] == "Some audio"

        # Verify the default filename was passed
        call_kwargs = client.audio.transcriptions.create.call_args
        file_arg = call_kwargs.kwargs.get("file") or call_kwargs[1].get("file")
        assert file_arg[0] == "audio.ogg"

    @patch("src.services.transcription.get_groq_client")
    async def test_handles_missing_duration(self, mock_get_client):
        """Groq may omit duration/language — getattr fallback should handle it."""
        client = AsyncMock()
        resp = MagicMock(spec=[])  # Empty spec → no attributes
        resp.text = "Audio text"
        client.audio.transcriptions.create = AsyncMock(return_value=resp)
        mock_get_client.return_value = client

        result = await transcribe_audio_bytes(b"bytes")
        assert result["text"] == "Audio text"
        assert result["duration"] is None
        assert result["language"] is None


@pytest.mark.asyncio
class TestTranscribeAudioFile:
    async def test_missing_file_raises(self):
        with pytest.raises(FileNotFoundError):
            await transcribe_audio("/nonexistent/path/audio.ogg")

    @patch("src.services.transcription.get_groq_client")
    async def test_reads_file_and_transcribes(self, mock_get_client, tmp_path):
        # Create a fake audio file
        audio_file = tmp_path / "test.ogg"
        audio_file.write_bytes(b"fake-audio-content")

        client = AsyncMock()
        client.audio.transcriptions.create = AsyncMock(
            return_value=_make_whisper_response(text="File transcription")
        )
        mock_get_client.return_value = client

        result = await transcribe_audio(str(audio_file))
        assert result["text"] == "File transcription"
