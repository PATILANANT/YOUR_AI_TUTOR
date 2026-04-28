# ========= MULTI-MODAL KNOWLEDGE SOURCES =========
# YouTube transcript extraction and Voice note transcription

import os
import tempfile
from config import client, MODEL_NAME


# ---------------------------------------------------
# 1. YOUTUBE TRANSCRIPT EXTRACTION
# ---------------------------------------------------

def extract_youtube_transcript(video_url: str) -> dict:
    """
    Extract transcript from a YouTube video URL.
    Returns dict with transcript, summary, and metadata.
    """
    from youtube_transcript_api import YouTubeTranscriptApi

    # Extract video ID from URL
    video_id = _parse_youtube_id(video_url)
    if not video_id:
        raise ValueError("Invalid YouTube URL. Please provide a valid YouTube video link.")

    try:
        # Fetch transcript
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        full_text = " ".join([entry['text'] for entry in transcript_list])

        # Calculate total duration
        total_duration = sum(entry.get('duration', 0) for entry in transcript_list)

        return {
            "video_id": video_id,
            "transcript": full_text,
            "duration_seconds": total_duration,
            "segment_count": len(transcript_list)
        }
    except Exception as e:
        raise ValueError(f"Could not extract transcript: {str(e)}. The video may not have captions available.")


def summarize_transcript(transcript: str) -> str:
    """
    Use Gemini to create a concise, structured summary of a video transcript.
    """
    prompt = f"""Summarize the following video transcript into a well-structured learning note.

Rules:
- Create clear section headings
- Extract key concepts and definitions
- List important points as bullet points
- Keep the summary concise but comprehensive (300-500 words)
- Include any formulas, numbers, or specific facts mentioned

Transcript:
{transcript[:8000]}"""

    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt
        )
        return response.text
    except Exception as e:
        return f"Summary generation failed: {str(e)}"


def _parse_youtube_id(url: str) -> str:
    """Extract YouTube video ID from various URL formats."""
    import re

    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})',
        r'(?:youtube\.com\/shorts\/)([a-zA-Z0-9_-]{11})',
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    # Maybe it's just a video ID
    if len(url) == 11 and all(c.isalnum() or c in '_-' for c in url):
        return url

    return None


# ---------------------------------------------------
# 2. VOICE NOTE TRANSCRIPTION (Using Whisper)
# ---------------------------------------------------

def transcribe_voice_note(audio_path: str) -> str:
    """
    Transcribe an audio file using OpenAI Whisper (local model).
    Uses the 'base' model for a good speed/accuracy balance.
    """
    try:
        import whisper
        model = whisper.load_model("base")
        result = model.transcribe(audio_path)
        return result.get("text", "")
    except ImportError:
        # Fallback: try using speech_recognition with Google's free API
        return _transcribe_fallback(audio_path)
    except Exception as e:
        raise ValueError(f"Transcription failed: {str(e)}")


def _transcribe_fallback(audio_path: str) -> str:
    """
    Fallback transcription using SpeechRecognition library with Google's free API.
    Works without installing the large Whisper model.
    """
    try:
        import speech_recognition as sr

        recognizer = sr.Recognizer()

        # Convert to WAV if needed (for webm/ogg from browser)
        wav_path = audio_path
        if not audio_path.endswith('.wav'):
            wav_path = _convert_to_wav(audio_path)

        with sr.AudioFile(wav_path) as source:
            audio_data = recognizer.record(source)

        text = recognizer.recognize_google(audio_data)

        # Cleanup temp wav if we converted
        if wav_path != audio_path and os.path.exists(wav_path):
            os.remove(wav_path)

        return text
    except Exception as e:
        raise ValueError(f"Fallback transcription failed: {str(e)}. Please install 'openai-whisper' for better results.")


def _convert_to_wav(input_path: str) -> str:
    """Convert audio file to WAV format using pydub."""
    try:
        from pydub import AudioSegment

        audio = AudioSegment.from_file(input_path)
        wav_path = input_path.rsplit('.', 1)[0] + '.wav'
        audio.export(wav_path, format='wav')
        return wav_path
    except ImportError:
        # If pydub is not installed, try to use the file as-is
        return input_path
    except Exception:
        return input_path
