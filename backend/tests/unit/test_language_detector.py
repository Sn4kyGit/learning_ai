"""
Unit tests for language detection service.

Tests the LanguageDetector service with various text samples
to ensure accurate language detection for supported languages.
"""

import pytest
from unittest.mock import patch, MagicMock

from backend.ai.language_detector import LanguageDetector, SUPPORTED_LANGUAGES


class TestLanguageDetector:
    """Test suite for LanguageDetector service."""

    def setup_method(self):
        """Set up test fixtures."""
        self.detector = LanguageDetector()

    def test_init_creates_detector_with_supported_languages(self):
        """Test that detector initializes with correct supported languages."""
        # Act
        detector = LanguageDetector()
        
        # Assert
        assert detector.get_supported_languages() == SUPPORTED_LANGUAGES
        assert len(detector.get_supported_languages()) == 6

    def test_detect_language_empty_text_returns_english(self):
        """Test that empty text defaults to English."""
        # Arrange
        test_cases = ["", "   ", None]
        
        for text in test_cases:
            # Act
            result = self.detector.detect_language(text)
            
            # Assert
            assert result == "en"

    def test_detect_language_short_text_returns_english(self):
        """Test that very short text defaults to English."""
        # Arrange
        short_text = "Hi"
        
        # Act
        result = self.detector.detect_language(short_text)
        
        # Assert
        assert result == "en"

    @patch('backend.ai.language_detector.LANGDETECT_AVAILABLE', False)
    def test_detect_language_without_langdetect_returns_english(self):
        """Test fallback when langdetect is not available."""
        # Arrange
        text = "This is a test text"
        
        # Act
        result = self.detector.detect_language(text)
        
        # Assert
        assert result == "en"

    @patch('backend.ai.language_detector.LANGDETECT_AVAILABLE', True)
    @patch('backend.ai.language_detector.detect')
    def test_detect_language_supported_language_returns_detected(self, mock_detect):
        """Test detection of supported languages."""
        # Arrange
        test_cases = [
            ("Das Essen war sehr gut und der Service ausgezeichnet", "de"),
            ("The food was excellent and service was great", "en"),
            ("Yemek çok lezzetliydi ve servis harikaydı", "tr"),
            ("Il cibo era delizioso e il servizio eccellente", "it"),
            ("La comida estaba deliciosa y el servicio excelente", "es"),
            ("La nourriture était délicieuse et le service excellent", "fr"),
        ]
        
        for text, expected_lang in test_cases:
            mock_detect.return_value = expected_lang
            
            # Act
            result = self.detector.detect_language(text)
            
            # Assert
            assert result == expected_lang
            mock_detect.assert_called_with(text.strip())

    @patch('backend.ai.language_detector.LANGDETECT_AVAILABLE', True)
    @patch('backend.ai.language_detector.detect')
    def test_detect_language_unsupported_language_returns_english(self, mock_detect):
        """Test that unsupported languages default to English."""
        # Arrange
        text = "Some text in unsupported language"
        mock_detect.return_value = "ja"  # Japanese - unsupported
        
        # Act
        result = self.detector.detect_language(text)
        
        # Assert
        assert result == "en"

    @patch('backend.ai.language_detector.LANGDETECT_AVAILABLE', True)
    @patch('backend.ai.language_detector.detect')
    def test_detect_language_exception_returns_english(self, mock_detect):
        """Test that detection exceptions default to English."""
        # Arrange
        text = "Test text"
        mock_detect.side_effect = Exception("Detection failed")
        
        # Act
        result = self.detector.detect_language(text)
        
        # Assert
        assert result == "en"

    def test_is_supported_language_valid_codes(self):
        """Test supported language validation."""
        # Arrange & Act & Assert
        assert self.detector.is_supported_language("en") is True
        assert self.detector.is_supported_language("de") is True
        assert self.detector.is_supported_language("tr") is True
        assert self.detector.is_supported_language("it") is True
        assert self.detector.is_supported_language("es") is True
        assert self.detector.is_supported_language("fr") is True
        
        # Test unsupported languages
        assert self.detector.is_supported_language("ja") is False
        assert self.detector.is_supported_language("zh") is False
        assert self.detector.is_supported_language("invalid") is False

    @patch('backend.ai.language_detector.LANGDETECT_AVAILABLE', True)
    @patch('backend.ai.language_detector.detect_langs')
    def test_detect_language_with_confidence_returns_language_and_score(self, mock_detect_langs):
        """Test language detection with confidence scores."""
        # Arrange
        text = "This is a test text"
        mock_detection = MagicMock()
        mock_detection.lang = "en"
        mock_detection.prob = 0.95
        mock_detect_langs.return_value = [mock_detection]
        
        # Act
        language, confidence = self.detector.detect_language_with_confidence(text)
        
        # Assert
        assert language == "en"
        assert confidence == 0.95

    @patch('backend.ai.language_detector.LANGDETECT_AVAILABLE', True)
    @patch('backend.ai.language_detector.detect_langs')
    def test_detect_language_with_confidence_unsupported_returns_english(self, mock_detect_langs):
        """Test confidence detection with unsupported language."""
        # Arrange
        text = "Test text"
        mock_detection = MagicMock()
        mock_detection.lang = "ja"  # Unsupported
        mock_detection.prob = 0.90
        mock_detect_langs.return_value = [mock_detection]
        
        # Act
        language, confidence = self.detector.detect_language_with_confidence(text)
        
        # Assert
        assert language == "en"
        assert confidence == 0.0

    def test_detect_language_with_confidence_empty_text(self):
        """Test confidence detection with empty text."""
        # Act
        language, confidence = self.detector.detect_language_with_confidence("")
        
        # Assert
        assert language == "en"
        assert confidence == 0.0

    def test_batch_detect_languages_multiple_texts(self):
        """Test batch language detection."""
        # Arrange
        texts = [
            "This is English text",
            "Das ist deutscher Text",
            "Bu Türkçe metin"
        ]
        
        with patch.object(self.detector, 'detect_language') as mock_detect:
            mock_detect.side_effect = ["en", "de", "tr"]
            
            # Act
            results = self.detector.batch_detect_languages(texts)
            
            # Assert
            assert results == ["en", "de", "tr"]
            assert mock_detect.call_count == 3

    def test_batch_detect_languages_empty_list(self):
        """Test batch detection with empty list."""
        # Act
        results = self.detector.batch_detect_languages([])
        
        # Assert
        assert results == []

    def test_get_supported_languages_returns_copy(self):
        """Test that supported languages returns a copy."""
        # Act
        languages1 = self.detector.get_supported_languages()
        languages2 = self.detector.get_supported_languages()
        
        # Assert
        assert languages1 == languages2
        assert languages1 is not languages2  # Different objects

    @patch('backend.ai.language_detector.LANGDETECT_AVAILABLE', True)
    def test_is_available_property_with_langdetect(self):
        """Test is_available property when langdetect is available."""
        # Act & Assert
        assert self.detector.is_available is True

    @patch('backend.ai.language_detector.LANGDETECT_AVAILABLE', False)
    def test_is_available_property_without_langdetect(self):
        """Test is_available property when langdetect is not available."""
        # Act & Assert
        assert self.detector.is_available is False