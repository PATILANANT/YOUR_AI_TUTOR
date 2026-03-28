from deep_translator import GoogleTranslator

LANGUAGE_CODES = {
    "Hindi": "hi", "Marathi": "mr", "Gujarati": "gu", "Punjabi": "pa",
    "Bengali": "bn", "Tamil": "ta", "Telugu": "te", "Kannada": "kn",
    "Malayalam": "ml", "Odia": "or", "Assamese": "as", "Urdu": "ur",
    "Nepali": "ne"
}

def translate_text(text, language):
    if language in LANGUAGE_CODES:
        try:
            return GoogleTranslator(source='auto', target=LANGUAGE_CODES[language]).translate(text)
        except:
            return text
    return text