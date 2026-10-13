import base64
from bhashini.client import BhashiniClient

def speech_to_text(audio_base64: str, language: str) -> dict:
    """
    Transcribes speech from audio base64.
    If Bhashini is configured, uses Bhashini ASR pipeline.
    Otherwise flags to use native client-side speech recognition.
    """
    client = BhashiniClient()
    
    if client.is_configured():
        # Future Bhashini ASR pipeline call
        return {
            "text": "",
            "language": language,
            "provider": "bhashini_official_asr"
        }
        
    return {
        "text": "",
        "language": language,
        "provider": "browser_speech_recognition"
    }
