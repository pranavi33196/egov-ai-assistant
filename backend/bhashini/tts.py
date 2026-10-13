"""
bhashini/tts.py  (patched)

Adds POST /api/tts/speak (text in the request body) so long Telugu/Hindi answers
no longer overflow the URL length limit. The old GET /api/tts/stream and the
text_to_speech() helper used by api/language.py are kept for compatibility.
"""
import io
import os
import re
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel

router = APIRouter()

TTS_MAX_CHARS = int(os.getenv("TTS_MAX_CHARS", "1500"))
_LANG_ALIASES = {
    "te": "te", "telugu": "te",
    "hi": "hi", "hindi": "hi",
    "ta": "ta", "tamil": "ta",
    "kn": "kn", "kannada": "kn",
}


def _lang_code(language: str) -> str:
    return _LANG_ALIASES.get((language or "en").lower().strip(), "en")


def clean_text_for_speech(text: str) -> str:
    """Strip markdown symbols and URLs so TTS reads cleanly."""
    cleaned = re.sub(r"https?://\S+", "", text)
    cleaned = re.sub(r"[*#_•\-\[\]\(\)]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned[:TTS_MAX_CHARS]


def text_to_speech(text: str, language: str = "en") -> dict:
    """Legacy helper used by api/language.py (POST /api/text-to-speech)."""
    lang_code = _lang_code(language)
    return {
        "status": "use_streaming_endpoint",
        "audio_url": f"/api/tts/stream?text={quote(text)}&lang={lang_code}",  # CHANGED: URL-encoded
        "language": lang_code,
    }


def _synthesize(text: str, lang: str) -> Response:
    cleaned = clean_text_for_speech(text)
    if not cleaned:
        raise HTTPException(status_code=400, detail="Empty speech text")
    try:
        from gtts import gTTS
        mp3_fp = io.BytesIO()
        gTTS(text=cleaned, lang=_lang_code(lang), slow=False).write_to_fp(mp3_fp)
        mp3_fp.seek(0)
        return Response(
            content=mp3_fp.read(),
            media_type="audio/mpeg",
            headers={"Cache-Control": "no-cache", "Content-Disposition": "inline; filename=tts.mp3"},
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"[TTS] gTTS generation error: {e}")
        raise HTTPException(status_code=500, detail=f"TTS synthesis error: {str(e)}")


class SpeakRequest(BaseModel):
    text: str
    lang: str = "en"


@router.post("/tts/speak")
def speak(req: SpeakRequest):
    """Preferred endpoint: text travels in the body, returns audio/mpeg."""
    return _synthesize(req.text, req.lang)


@router.get("/tts/stream")
def stream_text_to_speech(text: str = Query(..., min_length=1), lang: str = Query("en")):
    """Legacy GET endpoint (kept so nothing else breaks)."""
    return _synthesize(text, lang)
