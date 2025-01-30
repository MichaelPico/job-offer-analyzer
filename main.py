from utils.language_detector import LanguageDetector

def main():
    detector = LanguageDetector()

    test = "This is a test"
    language = detector.detect(test)

    print(language)

if __name__ == '__main__':
    main()

