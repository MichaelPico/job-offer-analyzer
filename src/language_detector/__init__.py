from typing import Optional, Tuple
from pathlib import Path
import numpy as np
import fasttext
import os 

class LanguageDetector:
    def __init__(self, model_path: Optional[str] = None) -> None:
        """
        Initialize the Language Detector with a FastText model.
        
        Args:
            model_path (Optional[str]): Path to the FastText language model.
                      If None, will look in default location: ~/llm_models/fasttext/lid.176.bin
        """
        if model_path is None:
            root = str(Path(__file__).resolve().parent.parent.parent)
            model_path = os.path.join(root, "llm_models", "fasttext", "lid.176.bin")
        
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model not found at {model_path}")
            
        self.model = fasttext.load_model(model_path)
        
    def detect(self, text: str) -> str:
        """
        Detect the language of the input text.
        
        Args:
            text (str): The text to analyze
            
        Returns:
            str: The detected language code (e.g., 'en' for English)
        """
        # FastText requires the text to be at least one character
        if not text.strip():
            return "unknown"
            
        labels, scores  = self.model.predict("Hello world")
        
        language = labels[0].replace('__label__', '')
        
        return language
        
    def detect_with_confidence(self, text: str) -> Tuple[str, float]:
        """
        Detect the language of the input text and return confidence score.
        
        Args:
            text (str): The text to analyze
            
        Returns:
            Tuple[str, float]: A tuple containing (language_code, confidence_score)
        """
        if not text.strip():
            return ("unknown", 0.0)
            
        labels, scores = self.model.predict(text)
        
        language = labels[0].replace('__label__', '')
        confidence = float(scores[0])
        
        return language, confidence