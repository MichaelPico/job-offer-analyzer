import pytest
import os
from unittest import mock
from pathlib import Path

# Add the src directory to the system path to import the LanguageDetector module
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))
from language_detector import LanguageDetector


@pytest.fixture
def mock_model():
    """Fixture to mock the fasttext model."""
    mock_model = mock.MagicMock()
    mock_model.predict.return_value = (["__label__en"], [0.99])
    return mock_model


def test_initialize_with_default_model_path(mock_model):
    # Setup mock for fasttext load_model
    with mock.patch("fasttext.load_model", return_value=mock_model) as mock_load_model:
        detector = LanguageDetector()
        assert detector.model == mock_model
        mock_load_model.assert_called_once_with(os.path.join(str(Path(__file__).resolve().parent.parent.parent), "llm_models", "fasttext", "lid.176.bin"))


def test_initialize_with_invalid_model_path():
    invalid_path = "nonexistent_model.bin"
    
    with pytest.raises(FileNotFoundError):
        LanguageDetector(model_path=invalid_path)


def test_detect_language(mock_model):
    detector = LanguageDetector()
    
    # Test with valid text
    result = detector.detect("Hello world")
    assert result == "en"
    
    # Test with empty text
    result = detector.detect("")
    assert result == "unknown"


def test_detect_with_confidence(mock_model):
    detector = LanguageDetector()
    
    # Test with valid text English
    language, confidence = detector.detect_with_confidence("To be, or not to be, that is the question: Whether 'tis nobler in the mind to suffer.")
    assert language == "en"
    assert confidence >= 0.8
    
    # Test with valid text French
    language, confidence = detector.detect_with_confidence("Fils d'un charpentier installé dans une petite ville de province, Julien Sorel rêve d'autres horizons..")
    assert language == "fr"
    assert confidence >= 0.8
    
    # Test with empty text
    language, confidence = detector.detect_with_confidence("")
    assert language == "unknown"
    assert confidence == 0.0
