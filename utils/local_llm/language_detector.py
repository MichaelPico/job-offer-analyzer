from typing import Optional, Tuple
from pathlib import Path
import numpy as np
import fasttext
import os 

class LanguageDetector:
    """
    A class for detecting the language of input text using a FastText model.

    This class loads a pre-trained FastText language identification model and provides methods 
    to detect the language of a given text. It can return just the language code or also include 
    the confidence score of the detection.
    """
    def __init__(self, model_path: Optional[str] = None) -> None:
        """
        Initialize the Language Detector with a FastText model.

        Args:
            model_path (Optional[str]): Path to the FastText language model.
                      If None, will first look for the environment variable 'LLM_FASTTEXT_MODEL_PATH'.
                      If the environment variable is not set or empty, it will look in the default location: ~/llm_models/fasttext/lid.176.bin.
        """
        # Check for the environment variable LLM_FASTTEXT_MODEL_PATH
        env_model_path = os.getenv('LLM_FASTTEXT_MODEL_PATH')

        # If the environment variable is set and not empty, use it
        if env_model_path:
            model_path = env_model_path
        elif model_path is None:
            # If model_path is not provided, use the default path
            root = str(Path(__file__).resolve().parent.parent.parent)
            model_path = os.path.join(root, "llm_models", "fasttext", "lid.176.bin")

        # Check if the model file exists at the specified path
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model not found at {model_path}")

        # Load the FastText model
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