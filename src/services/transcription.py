# Service: Audio transcription using Groq Whisper API

import asyncio
import logging
import os

from src.config import get_settings
from src.services.groq_client import get_groq_client

logger = logging.getLogger(__name__)


async def transcribe_audio(file_path: str) -> dict:
    """
    Transcribe an audio file using Groq Whisper.
    Returns dict with 'text' and 'duration' keys.
    """
    if not await asyncio.to_thread(os.path.exists, file_path):
        raise FileNotFoundError(f"Audio file not found: {file_path}")

    logger.info(f"Transcribing audio file: {file_path}")

    settings = get_settings()
    client = get_groq_client()

    def _read_file():
        with open(file_path, "rb") as f:
            return f.read()

    audio_bytes = await asyncio.to_thread(_read_file)
    transcription = await client.audio.transcriptions.create(
        model=settings.groq_whisper_model,
        file=(os.path.basename(file_path), audio_bytes),
        response_format="verbose_json",
    )

    logger.info(f"Transcription complete: {len(transcription.text)} chars")

    return {
        "text": transcription.text,
        "duration": getattr(transcription, "duration", None),
        "language": getattr(transcription, "language", None),
    }


async def transcribe_audio_bytes(audio_bytes: bytes, filename: str = "audio.ogg") -> dict:
    """
    Transcribe audio from bytes.
    """
    logger.info(f"Transcribing audio bytes: {len(audio_bytes)} bytes")

    settings = get_settings()
    client = get_groq_client()

    transcription = await client.audio.transcriptions.create(
        model=settings.groq_whisper_model,
        file=(filename, audio_bytes),
        response_format="verbose_json",
    )

    logger.info(f"Transcription complete: {len(transcription.text)} chars")

    return {
        "text": transcription.text,
        "duration": getattr(transcription, "duration", None),
        "language": getattr(transcription, "language", None),
    }
