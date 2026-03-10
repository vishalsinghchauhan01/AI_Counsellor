import os
import io
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from openai import OpenAI

router = APIRouter()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


class TTSRequest(BaseModel):
    text: str
    voice: str = "nova"  # nova, alloy, shimmer, onyx, echo, fable


@router.post("/stt")
async def speech_to_text(audio: UploadFile = File(...)):
    """Convert audio to text using Whisper"""
    try:
        audio_bytes = await audio.read()
        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = audio.filename or "audio.webm"

        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
        )
        return {"text": transcript.text, "detected_language": "auto"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"STT Error: {str(e)}")


@router.post("/tts")
async def text_to_speech(req: TTSRequest):
    """Convert text to speech"""
    try:
        # Limit text length for TTS (OpenAI has 4096 char limit)
        text = req.text[:4096]

        response = client.audio.speech.create(
            model="tts-1",
            voice=req.voice,
            input=text,
            response_format="mp3"
        )
        audio_bytes = response.content
        return Response(
            content=audio_bytes,
            media_type="audio/mpeg",
            headers={"Content-Disposition": "attachment; filename=response.mp3"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS Error: {str(e)}")
