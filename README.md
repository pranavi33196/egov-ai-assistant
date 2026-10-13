# AI-Based Multilingual Query Assistant for e-Governance

## Problem Statement
Citizens often face challenges accessing accurate, official information regarding government services due to language barriers, complex bureaucratic terminology, and fragmented information sources.

## Proposed Solution
An AI-powered multilingual virtual assistant that enables citizens to ask service-related questions in their native language (text or voice), processes the query using a retrieval-augmented generation (RAG) approach against a curated government knowledge base, and returns a grounded, translated response with source attribution.

## Objectives
1. Provide accurate, context-aware answers to government service queries.
2. Bridge the language gap using BHASHINI translation and voice capabilities.
3. Eliminate AI hallucination by strictly grounding responses in official documents.
4. Provide a secure, prototype SSO integration for authorized access.

## Architecture
```text
Citizen
   ↓
React + Vite Frontend
   ↓
Prototype SSO
   ↓
FastAPI Backend
   ↓
Language Layer
   ↓
BHASHINI
   ↓
Intent Detection
   ↓
RAG Engine
   ↓
Sentence Transformers
   ↓
ChromaDB
   ↓
Ollama / Fallback LLM
   ↓
Grounded Response
   ↓
BHASHINI Translation
   ↓
TTS
   ↓
Citizen
```

## Technology Stack
- **Frontend**: React, Vite, Tailwind CSS, Lucide React
- **Backend**: FastAPI, Python, Uvicorn
- **AI/RAG**: ChromaDB, Sentence-Transformers, Ollama (Local)
- **Language**: Bhashini (Mock & Ready for Real credentials)
- **Auth**: Prototype JWT SSO

## Features
- Prototype SSO authentication.
- Multilingual query support (English, Telugu, Hindi).
- Voice Input (Simulated/Web API).
- Text-to-Speech (Web API).
- RAG pipeline ensuring responses are sourced from a controlled knowledge base.
- Automatic fallback LLM generation if Ollama is unavailable.
- Real-time system status indicators.

## Folder Structure
- `backend/`: FastAPI application, AI logic, vector DB, auth module, and Bhashini integrations.
- `frontend/`: React UI components and API service integration.
- `docs/`: Architecture and project flow documentation.

## Installation & Setup

### Prerequisites
- Python 3.9+
- Node.js 18+
- (Optional) Ollama installed and running `llama3` locally.

### Environment Variables (Backend)
Copy `backend/.env.example` to `backend/.env` and update:
```env
JWT_SECRET=supersecret_demo_key
BHASHINI_MODE=mock
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3
```

### Backend Startup
```bash
cd backend
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/Mac:
# source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Frontend Startup
```bash
cd frontend
npm install
npm run dev
```

## Demo
- **Frontend URL**: `http://localhost:5173`
- **Backend URL**: `http://localhost:8000/docs`
- **Demo Credentials**: Username: `demo` / Password: `demo123`

### Sample Queries
- English: "How can I apply for a ration card?"
- Telugu: "రేషన్ కార్డు కోసం ఎలా దరఖాస్తు చేయాలి?"
- Hindi: "राशन कार्ड के लिए आवेदन कैसे करें?"

## Configuration Modes
- **BHASHINI Mock Mode**: `BHASHINI_MODE=mock`. Simulates translations and ASR/TTS endpoints to ensure the application is demonstrable offline.
- **LLM Fallback**: If Ollama is unavailable, a deterministic summary engine automatically takes over using the retrieved RAG context.

## Prototype Limitations & Future Enhancements
- **Limitations**: The current knowledge base is a prototype. SSO is mocked.
- **Future**: Connect to real state e-district APIs, real BHASHINI credentials, and an official identity provider (like DigiLocker/e-Pramaan).
- **Security Considerations**: For production, move away from local SQLite/Chroma file storage to managed cloud instances, enforce HTTPS, validate JWTs against an external OIDC provider, and implement rate limiting.
