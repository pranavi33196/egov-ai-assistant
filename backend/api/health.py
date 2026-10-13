from fastapi import APIRouter
from pydantic import BaseModel
import os
from dotenv import load_dotenv

load_dotenv()

router = APIRouter()

class HealthResponse(BaseModel):
    status: str
    message: str
    bhashini_mode: str
    llm_provider: str

@router.get("/health", response_model=HealthResponse)
def health_check():
    return HealthResponse(
        status="ok",
        message="e-Gov AI Assistant API is running.",
        bhashini_mode=os.getenv("BHASHINI_MODE", "mock"),
        llm_provider=os.getenv("LLM_PROVIDER", "auto")
    )

@router.get("/", include_in_schema=False)
def root():
    return {"message": "Welcome to e-Gov AI Assistant API"}
