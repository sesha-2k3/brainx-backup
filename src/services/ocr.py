"""
Service: OCR processing for business cards using Tesseract
"""

import asyncio
import io
import logging
import os
from concurrent.futures import ThreadPoolExecutor

import pytesseract
from PIL import Image

from src.services.extraction import extract_contact_data

logger = logging.getLogger(__name__)

# Threadpool for blocking OCR operations.
_executor = ThreadPoolExecutor(max_workers=4)


def _run_ocr_sync(image_bytes: bytes) -> tuple[str, float]:
    """Synchronous OCR processing (runs in thread pool)."""
    image = Image.open(io.BytesIO(image_bytes))
    raw_text = pytesseract.image_to_string(image)

    ocr_data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
    confidences = [c for c in ocr_data["conf"] if c > 0]
    avg_confidence = sum(confidences) / len(confidences) if confidences else 0

    return raw_text, avg_confidence / 100


def _read_file_sync(file_path: str) -> bytes:
    with open(file_path, "rb") as fh:
        return fh.read()


async def process_business_card(file_path: str) -> dict:
    """
    Process a business card image from a path on disk.
    Returns dict with raw text, extracted data, and confidence in 0.0-1.0.

    Delegates to the same _run_ocr_sync() helper as the bytes variant. It used
    to duplicate that logic inline, which caused two bugs: PIL and pytesseract
    ran directly on the event loop (both are blocking), and the two paths
    disagreed on the confidence scale - the bytes path returned 0.0-1.0 while
    this one returned 0-100. One code path means they can't drift again.
    """
    if not await asyncio.to_thread(os.path.exists, file_path):
        raise FileNotFoundError(f"Image file not found: {file_path}")

    logger.info(f"Processing business card: {file_path}")

    image_bytes = await asyncio.to_thread(_read_file_sync, file_path)
    return await process_business_card_bytes(image_bytes)


async def process_business_card_bytes(image_bytes: bytes) -> dict:
    """
    Process a business card from raw bytes.
    Returns dict with raw text, extracted data, and confidence in 0.0-1.0.
    """
    logger.info(f"Processing business card bytes: {len(image_bytes)} bytes")

    loop = asyncio.get_running_loop()

    # Run blocking OCR (PIL decode + tesseract) in the thread pool
    raw_text, confidence = await loop.run_in_executor(_executor, _run_ocr_sync, image_bytes)
    logger.info(f"OCR extracted {len(raw_text)} chars (confidence {confidence:.2f})")

    # extract_contact_data() already runs the email/phone/website regex passes
    # internally on the full raw_text before calling the LLM - no separate
    # quick-extract/merge step is needed here.
    extracted = await extract_contact_data(raw_text)

    return {
        "raw_text": raw_text,
        "confidence": confidence,
        "extracted": extracted,
    }
