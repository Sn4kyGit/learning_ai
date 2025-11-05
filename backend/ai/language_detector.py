"""
Language detection service using langdetect library.

This module provides language detection capabilities for customer reviews
supporting German, English, Turkish, Italian, Spanish, and French.
"""

import logging
from typing import Optional

try:
    from langdetect import detect, detect_langs, DetectorFactory
    # Set seed for consistent results
    DetectorFactory.seed = 0
    LANGDETECT_AVAILABLE = True
except ImportError:
    LANGDETECT_AVAILABLE = False

logger = logging.getLogger(__name__)

SUPPORTED_LANGUAGES = {
    "de": "German",
    "en": "English",
    "tr": "Turkish",
    "it": "Italian",
    "es": "Spanish",
    "fr": "French",
}


class LanguageDetector:
    """Language detection service for review text."""

    def __init__(self):
        """Initialize language detector."""
        self._supported_languages = SUPPORTED_LANGUAGES

    def detect_language(self, text: str) -> str:
        """Detect the language of the given text.

        Args:
            text: Text to analyze for language detection

        Returns:
            Language code (e.g., 'en', 'de', 'tr') or 'en' as fallback
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for language detection")
            return "en"

        if not LANGDETECT_AVAILABLE:
            logger.warning("langdetect library not available, defaulting to English")
            return "en"

        try:
            # Clean text for better detection
            cleaned_text = text.strip()
            
            # Skip very short texts as they're unreliable for detection
            if len(cleaned_text) < 10:
                logger.debug("Text too short for reliable detection, defaulting to English")
                return "en"

            detected = detect(cleaned_text)

            if detected in self._supported_languages:
                logger.debug(f"Detected language: {detected} ({self._supported_languages[detected]})")
                return detected
            else:
                logger.warning(f"Unsupported language detected: {detected}, defaulting to English")
                return "en"

        except Exception as e:
            logger.error(f"Language detection failed: {e}")
            return "en"

    def is_supported_language(self, language_code: str) -> bool:
        """Check if a language code is supported.

        Args:
            language_code: Language code to check

        Returns:
            True if language is supported, False otherwise
        """
        return language_code in self._supported_languages

    def detect_language_with_confidence(self, text: str) -> tuple[str, float]:
        """Detect language with confidence score.

        Args:
            text: Text to analyze for language detection

        Returns:
            Tuple of (language_code, confidence_score)
        """
        if not text or not text.strip():
            return "en", 0.0

        if not LANGDETECT_AVAILABLE:
            return "en", 0.0

        try:
            cleaned_text = text.strip()
            if len(cleaned_text) < 10:
                return "en", 0.0

            detections = detect_langs(cleaned_text)
            
            # Get the most confident detection
            best_detection = detections[0]
            language_code = best_detection.lang
            confidence = best_detection.prob

            if language_code in self._supported_languages:
                return language_code, confidence
            else:
                logger.warning(f"Unsupported language detected: {language_code}")
                return "en", 0.0

        except Exception as e:
            logger.error(f"Language detection with confidence failed: {e}")
            return "en", 0.0

    def batch_detect_languages(self, texts: list[str]) -> list[str]:
        """Detect languages for multiple texts efficiently.

        Args:
            texts: List of texts to analyze

        Returns:
            List of language codes in same order as input
        """
        results = []
        for text in texts:
            language = self.detect_language(text)
            results.append(language)
        return results

    def get_supported_languages(self) -> dict:
        """Get dictionary of supported language codes and names.

        Returns:
            Dictionary mapping language codes to language names
        """
        return self._supported_languages.copy()

    @property
    def is_available(self) -> bool:
        """Check if language detection is available.

        Returns:
            True if langdetect library is available, False otherwise
        """
        return LANGDETECT_AVAILABLE
