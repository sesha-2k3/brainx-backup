# Service: OCR processing for business cards using Tesseract

import logging
import re
import asyncio
import io
from pathlib import Path

import pytesseract
from PIL import Image
from concurrent.futures import ThreadPoolExecutor

from src.schemas.contacts import ExtractedContactData
from src.services.extraction import extract_contact_data

logger = logging.getLogger(__name__)

# Threadpool for blocking OCR operations.
_executor = ThreadPoolExecutor(max_workers=4)

# Common patterns for extraction
EMAIL_PATTERN = re.compile(r'[\w\.-]+@[\w\.-]+\.\w+')
PHONE_PATTERN = re.compile(r'[\+]?[(]?[0-9]{1,3}[)]?[-\s\.]?[(]?[0-9]{1,4}[)]?[-\s\.]?[0-9]{1,4}[-\s\.]?[0-9]{1,9}')
URL_PATTERN = re.compile(r'https?://[^\s]+|www\.[^\s]+')

def _run_ocr_sync(image_bytes: bytes) -> tuple[str, float]:
    """Synchronous OCR processing (runs in thread pool)."""
    image = Image.open(io.BytesIO(image_bytes))
    raw_text = pytesseract.image_to_string(image)
    
    ocr_data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
    confidences = [c for c in ocr_data['conf'] if c > 0]
    avg_confidence = sum(confidences) / len(confidences) if confidences else 0
    
    return raw_text, avg_confidence / 100

async def process_business_card(file_path: str) -> dict:
    """
    Process a business card image using OCR.
    Returns dict with raw text and extracted data.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Image file not found: {file_path}")
    
    logger.info(f"Processing business card: {file_path}")
    
    # Open and preprocess image
    image = Image.open(file_path)
    
    # Run OCR
    raw_text = pytesseract.image_to_string(image)
    logger.info(f"OCR extracted {len(raw_text)} chars")
    
    # Get confidence data
    ocr_data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
    confidences = [c for c in ocr_data['conf'] if c > 0]
    avg_confidence = sum(confidences) / len(confidences) if confidences else 0
    
    # Quick regex extraction as fallback
    quick_extract = _quick_extract(raw_text)
    
    # Use LLM for better extraction
    extracted = await extract_contact_data(raw_text)
    
    # Merge quick extract for any missing fields
    if not extracted.email and quick_extract.get("email"):
        extracted.email = quick_extract["email"]
    if not extracted.phone and quick_extract.get("phone"):
        extracted.phone = quick_extract["phone"]
    
    return {
        "raw_text": raw_text,
        "confidence": avg_confidence / 100,  # Normalize to 0-1
        "extracted": extracted,
    }


async def process_business_card_bytes(image_bytes: bytes) -> dict:
    """Process business card from bytes."""
    logger.info(f"Processing business card bytes: {len(image_bytes)} bytes")
    
    loop = asyncio.get_event_loop()
    
    # Run blocking OCR in thread pool
    raw_text, confidence = await loop.run_in_executor(
        _executor, 
        _run_ocr_sync, 
        image_bytes
    )
    
    quick_extract = _quick_extract(raw_text)
    extracted = await extract_contact_data(raw_text)
    
    if not extracted.email and quick_extract.get("email"):
        extracted.email = quick_extract["email"]
    if not extracted.phone and quick_extract.get("phone"):
        extracted.phone = quick_extract["phone"]
    
    return {
        "raw_text": raw_text,
        "confidence": confidence,
        "extracted": extracted,
    }


def _quick_extract(text: str) -> dict:
    """
    Quick regex-based extraction as fallback.
    """
    result = {}
    
    # Extract email
    emails = EMAIL_PATTERN.findall(text)
    if emails:
        result["email"] = emails[0].lower()
    
    # Extract phone
    phones = PHONE_PATTERN.findall(text)
    if phones:
        # Clean up phone number
        phone = re.sub(r'[^\d+]', '', phones[0])
        result["phone"] = phone
    
    # Extract URL (feature to be added in future)
    urls = URL_PATTERN.findall(text)
    if urls:
        result["url"] = urls[0]
    
    return result
