"""
Service: OCR processing for business cards using Tesseract
"""

import asyncio
import io
import logging
import os
import re
from concurrent.futures import ThreadPoolExecutor

import pytesseract
from PIL import Image

from src.services.extraction import extract_contact_data

logger = logging.getLogger(__name__)

# Threadpool for blocking OCR operations.
_executor = ThreadPoolExecutor(max_workers=4)

# URL isn't part of ExtractedContactData yet (flagged as a future field in the
# original code) - kept here since it's OCR-specific metadata, not something
# extract_contact_data() returns. Email/phone regex now lives in
# src/utils/phone.py and src/utils/text.py and is applied once, inside
# extract_contact_data() itself - no need to duplicate or merge it here.
URL_PATTERN = re.compile(r"https?://[^\s]+|www\.[^\s]+")


def _run_ocr_sync(image_bytes: bytes) -> tuple[str, float]:
    """Synchronous OCR processing (runs in thread pool)."""
    image = Image.open(io.BytesIO(image_bytes))
    raw_text = pytesseract.image_to_string(image)

    ocr_data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
    confidences = [c for c in ocr_data["conf"] if c > 0]
    avg_confidence = sum(confidences) / len(confidences) if confidences else 0

    return raw_text, avg_confidence / 100


async def process_business_card(file_path: str) -> dict:
    """
    Process a business card image using OCR.
    Returns dict with raw text and extracted data.
    """
    if not await asyncio.to_thread(os.path.exists, file_path):
        raise FileNotFoundError(f"Image file not found: {file_path}")

    logger.info(f"Processing business card: {file_path}")

    # Open and preprocess image
    image = Image.open(file_path)

    # Run OCR
    raw_text = pytesseract.image_to_string(image)
    logger.info(f"OCR extracted {len(raw_text)} chars")

    # Get confidence data
    ocr_data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
    confidences = [c for c in ocr_data["conf"] if c > 0]
    avg_confidence = sum(confidences) / len(confidences) if confidences else 0

    # extract_contact_data() already runs the email/phone regex pass
    # internally (on the full raw_text) before ever calling the LLM - no
    # separate quick-extract/merge step needed here anymore.
    extracted = await extract_contact_data(raw_text)

    urls = URL_PATTERN.findall(raw_text)

    return {
        "raw_text": raw_text,
        "confidence": avg_confidence,
        "extracted": extracted,
        "url": urls[0] if urls else None,
    }


async def process_business_card_bytes(image_bytes: bytes) -> dict:
    """Process business card from bytes."""
    logger.info(f"Processing business card bytes: {len(image_bytes)} bytes")

    loop = asyncio.get_event_loop()

    # Run blocking OCR in thread pool
    raw_text, confidence = await loop.run_in_executor(_executor, _run_ocr_sync, image_bytes)

    extracted = await extract_contact_data(raw_text)
    urls = URL_PATTERN.findall(raw_text)

    return {
        "raw_text": raw_text,
        "confidence": confidence,
        "extracted": extracted,
        "url": urls[0] if urls else None,
    }
