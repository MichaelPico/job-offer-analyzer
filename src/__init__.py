from language_detector import LanguageDetector

detector = LanguageDetector()

test = "This is a test"
language = detector.detect(test)

print(language)