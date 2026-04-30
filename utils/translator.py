from deep_translator import GoogleTranslator

LANGUAGE_CODES = {
    "Hindi": "hi", "Marathi": "mr", "Gujarati": "gu", "Punjabi": "pa",
    "Bengali": "bn", "Tamil": "ta", "Telugu": "te", "Kannada": "kn",
    "Malayalam": "ml", "Odia": "or", "Assamese": "as", "Urdu": "ur",
    "Nepali": "ne"
}

def translate_text(text, language):
    """Translate text FROM English TO the target language."""
    if language in LANGUAGE_CODES:
        try:
            return GoogleTranslator(source='auto', target=LANGUAGE_CODES[language]).translate(text)
        except:
            return text
    return text


def translate_to_english(text, source_language=None):
    """
    Translate user input TO English before sending to Gemini.
    This saves tokens because English is 2-3x more token-efficient
    than Hindi, Marathi, etc.
    
    Args:
        text: The user's input text (possibly in a non-English language)
        source_language: The language name (e.g., "Hindi"). If None, auto-detect.
    
    Returns:
        The text translated to English (or original if already English)
    """
    if not text or not text.strip():
        return text

    # Skip if user is already using English
    if source_language and source_language == "English":
        return text

    try:
        translated = GoogleTranslator(source='auto', target='en').translate(text)
        return translated if translated else text
    except:
        return text