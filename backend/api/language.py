from fastapi import APIRouter, File, UploadFile, Form, HTTPException
from pydantic import BaseModel
from bhashini.translate import translate_text
from bhashini.tts import text_to_speech
from bhashini.asr import speech_to_text

router = APIRouter()

class TranslateRequest(BaseModel):
    text: str
    source_language: str
    target_language: str

class TTSRequest(BaseModel):
    text: str
    language: str

@router.post("/translate")
def api_translate(request: TranslateRequest):
    return translate_text(request.text, request.source_language, request.target_language)

@router.post("/text-to-speech")
def api_tts(request: TTSRequest):
    return text_to_speech(request.text, request.language)

@router.post("/speech-to-text")
async def api_asr(file: UploadFile = File(None), language: str = Form(...)):
    if not file:
        return speech_to_text(b"", language)
    
    audio_bytes = await file.read()
    return speech_to_text(audio_bytes, language)
