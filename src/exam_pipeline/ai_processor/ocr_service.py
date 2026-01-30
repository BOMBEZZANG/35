"""
OCR service with Google Cloud Vision and Tesseract fallback.

Handles image BLOB → text conversion for AI processing.
"""

import logging
from typing import Optional

from google.api_core.exceptions import Forbidden, GoogleAPIError, Unauthorized
from google.cloud import vision
from PIL import Image
import pytesseract
import io

logger = logging.getLogger(__name__)


class OCRService:
    """
    OCR service with dual-engine support.

    Primary: Google Cloud Vision API (high accuracy)
    Fallback: Tesseract OCR (local, no API costs)
    """

    def __init__(self):
        """Initialize OCR service with Google Vision client."""
        self.vision_client = None
        self._init_vision_client()

    def _init_vision_client(self):
        """Initialize Google Cloud Vision async client."""
        try:
            self.vision_client = vision.ImageAnnotatorAsyncClient()
            logger.info("Google Cloud Vision client initialized successfully")
        except Exception as e:
            logger.warning(f"Google Cloud Vision initialization failed: {e}")
            logger.warning("Will use Tesseract OCR as fallback")
            self.vision_client = None

    def is_valid_image_blob(self, blob_data: bytes) -> bool:
        """
        Check if BLOB is a valid image.

        Args:
            blob_data: Image bytes

        Returns:
            True if valid image BLOB
        """
        if not isinstance(blob_data, bytes) or len(blob_data) < 100:
            return False

        try:
            header = blob_data[:12]
            return (
                header.startswith(b'\xff\xd8') or  # JPEG
                header.startswith(b'\x89PNG\r\n\x1a\n') or  # PNG
                header.startswith(b'GIF87a') or
                header.startswith(b'GIF89a')  # GIF
            )
        except Exception:
            return False

    async def extract_text_from_blob(self, blob_data: bytes, context: str = "") -> str:
        """
        Extract text from image BLOB using OCR.

        Strategy:
        1. Try Google Cloud Vision API (high accuracy)
        2. Fall back to Tesseract OCR if Vision fails

        Args:
            blob_data: Image bytes
            context: Context for logging (e.g., "Question #5")

        Returns:
            Extracted text or empty string if extraction fails
        """
        if not self.is_valid_image_blob(blob_data):
            logger.debug(f"{context} - Not a valid image BLOB")
            return ""

        # Try Google Cloud Vision first
        if self.vision_client:
            result = await self._google_vision_ocr(blob_data, context)
            if result and not result.startswith("(OCR"):
                return result
            else:
                logger.warning(f"{context} - Google Vision failed, falling back to Tesseract")

        # Fallback to Tesseract
        return self._tesseract_ocr(blob_data, context)

    async def _google_vision_ocr(self, blob_data: bytes, context: str) -> str:
        """
        Extract text using Google Cloud Vision API.

        Args:
            blob_data: Image bytes
            context: Context for logging

        Returns:
            Extracted text or error message
        """
        try:
            image = vision.Image(content=blob_data)
            response = await self.vision_client.text_detection(image=image)

            if response.error.message:
                error_msg = f"(OCR Error: {response.error.message})"
                logger.warning(f"{context} - Google Vision API error: {response.error.message}")
                return error_msg

            texts = response.text_annotations
            if texts:
                extracted_text = texts[0].description.strip()
                logger.debug(f"{context} - Google Vision extracted {len(extracted_text)} chars")
                return extracted_text
            else:
                logger.debug(f"{context} - Google Vision found no text")
                return ""

        except (Forbidden, Unauthorized) as e:
            error_msg = f"(OCR Auth Error: {str(e)})"
            logger.error(f"{context} - Google Vision authentication error: {e}")
            return error_msg

        except GoogleAPIError as e:
            error_msg = f"(OCR API Error: {str(e)})"
            logger.error(f"{context} - Google Vision API error: {e}")
            return error_msg

        except Exception as e:
            error_msg = f"(OCR Unexpected Error: {str(e)})"
            logger.error(f"{context} - Unexpected error in Google Vision: {e}")
            return error_msg

    def _tesseract_ocr(self, blob_data: bytes, context: str) -> str:
        """
        Extract text using Tesseract OCR (local fallback).

        Args:
            blob_data: Image bytes
            context: Context for logging

        Returns:
            Extracted text or empty string
        """
        try:
            # Open image from bytes
            image = Image.open(io.BytesIO(blob_data))

            # Use Tesseract with Korean language support
            custom_config = r'--oem 3 --psm 6 -l kor+eng'
            text = pytesseract.image_to_string(image, config=custom_config)

            extracted_text = text.strip()
            logger.debug(f"{context} - Tesseract extracted {len(extracted_text)} chars")
            return extracted_text

        except pytesseract.TesseractNotFoundError:
            logger.error(f"{context} - Tesseract not installed. Install with: brew install tesseract tesseract-lang")
            return ""

        except Exception as e:
            logger.error(f"{context} - Tesseract OCR failed: {e}")
            return ""

    def close(self):
        """Close Vision client if initialized."""
        if self.vision_client:
            # AsyncClient doesn't need explicit close
            pass
