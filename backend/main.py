from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

# Load .env variables FIRST before any app import reads os.getenv
try:
    from dotenv import load_dotenv
    import pathlib
    load_dotenv(dotenv_path=pathlib.Path(__file__).parent / ".env")
except ImportError:
    pass

from database.base import engine, Base
import database.models  # registers all SQLAlchemy tables
from api import health, auth_v2 as auth, oauth, conversations, query, language
from bhashini import tts

# Create database tables automatically
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="AI-Based Multilingual Query Assistant for e-Governance",
    description="Multilingual e-Governance Assistant using Bhashini, SSO, RAG and LLM",
    version="2.0.0"
)

# CORS Configuration for React/Vite frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:5175",
        "http://localhost:3000",
        "*"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register all Routers
app.include_router(health.router, prefix="/api", tags=["health"])
app.add_api_route("/", health.root, methods=["GET"], tags=["root"])
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(oauth.router, prefix="/api/oauth", tags=["oauth"])
app.include_router(conversations.router, prefix="/api", tags=["conversations"])
app.include_router(query.router, prefix="/api", tags=["query"])
app.include_router(language.router, prefix="/api", tags=["language"])
app.include_router(tts.router, prefix="/api", tags=["tts"])

@app.get("/api/system/status")
def system_status():
    from bhashini.client import BhashiniClient
    from auth.email_service import is_email_configured
    from auth.captcha import is_captcha_configured
    from api.oauth import is_google_configured

    bhashini_cli = BhashiniClient()
    return {
        "database": "sqlite_connected",
        "rag_engine": "chromadb_active",
        "bhashini": "configured" if bhashini_cli.is_configured() else "neural_nmt_active",
        "email_service": "configured" if is_email_configured() else "not_configured",
        "captcha": "configured" if is_captcha_configured() else "dev_bypass_mode",
        "google_oauth": "configured" if is_google_configured() else "not_configured",
        "tts": "gtts_active"
    }


@app.get("/api/auth/smtp-health")
def smtp_health():
    """
    Safe diagnostic endpoint that tests the real SMTP connection.
    Reports 'SMTP: CONNECTED' only when credentials are valid and auth succeeds.
    NEVER exposes SMTP_PASSWORD or any credentials in the response.
    """
    from auth.email_service import smtp_health_check, is_email_configured, SMTP_HOST, SMTP_PORT, SMTP_FROM
    ok, message = smtp_health_check()
    return {
        "smtp_status": message,
        "connected": ok,
        "host": SMTP_HOST if SMTP_HOST else "not set",
        "port": SMTP_PORT,
        "sender": SMTP_FROM if SMTP_FROM else "not set",
        # SMTP_USERNAME and SMTP_PASSWORD are deliberately NOT included in this response
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
