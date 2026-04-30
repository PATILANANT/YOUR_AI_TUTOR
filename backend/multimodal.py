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
    Supports youtube-transcript-api v1.x (fetch) and legacy v0.x (get_transcript).
    """
    from youtube_transcript_api import YouTubeTranscriptApi

    # Extract video ID from URL
    video_id = _parse_youtube_id(video_url)
    if not video_id:
        raise ValueError("Invalid YouTube URL. Please provide a valid YouTube video link.")

    try:
        # v1.x API: instance-based with fetch()
        ytt = YouTubeTranscriptApi()
        transcript_obj = ytt.fetch(video_id)

        # v1.x returns a FetchedTranscript with .snippets
        snippets = transcript_obj.snippets
        full_text = " ".join([s.text for s in snippets])
        total_duration = sum(s.duration for s in snippets)

        return {
            "video_id": video_id,
            "transcript": full_text,
            "duration_seconds": total_duration,
            "segment_count": len(snippets)
        }
    except AttributeError:
        # Fallback for older v0.x API
        try:
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
            full_text = " ".join([entry['text'] for entry in transcript_list])
            total_duration = sum(entry.get('duration', 0) for entry in transcript_list)
            return {
                "video_id": video_id,
                "transcript": full_text,
                "duration_seconds": total_duration,
                "segment_count": len(transcript_list)
            }
        except Exception as e:
            raise ValueError(f"Could not extract transcript: {str(e)}. The video may not have captions available.")
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
