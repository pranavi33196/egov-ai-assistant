# Architecture Document

## High-Level Architecture Flow
This MVP utilizes a decoupled frontend and backend architecture designed to ensure resilience, modularity, and ease of future integration with external real-world systems like an OIDC identity provider or the actual BHASHINI APIs.

```text
Citizen (Browser/Mobile)
       |
       v
React + Vite Frontend (UI Layer)
       |
       |  (1) JWT Auth & Queries
       v
Prototype SSO / Auth Module
       |
       |  (2) Translation & Intent
       v
FastAPI Backend (Logic Layer)
       |
       +---> BHASHINI Adapter (Mock / Real)
       |      - Speech to Text
       |      - Text Translation
       |      - Text to Speech
       |
       +---> Intent Detection Engine (Rule-based)
       |
       +---> RAG Engine (Retrieval-Augmented Generation)
              |
              +---> Sentence Transformers (Embeddings)
              |
              +---> ChromaDB (Vector Search of Knowledge Base)
              |
              v
       LLM Engine Layer
       (Auto-Fallback Strategy)
              |
              +---> Ollama (Local LLM if available)
              |
              +---> Deterministic Fallback (if LLM unavailable)
```

## Component Details

### 1. Frontend (React + Tailwind CSS)
- **Framework**: Vite + React
- **Styling**: Tailwind CSS configured with a specific professional government-tech color palette.
- **Routing**: `react-router-dom` guarding authenticated routes.
- **State Management**: React Hooks (`useState`, `useEffect`).
- **Network**: `axios` for API calls, interceptors for JWT injection.

### 2. Backend (FastAPI)
- **Framework**: Python FastAPI running on Uvicorn.
- **Auth Module**: `auth/sso.py` provides a mock implementation generating standard JWTs to demonstrate the flow.
- **Language Layer**: `bhashini/client.py` uses `.env` configurations to toggle between a `mock` mode (for offline, standalone demos) and a `real` mode.
- **AI Modules**:
  - `ai/rag.py`: Implements the RAG architecture. Reads `.txt` files from `knowledge_base`, chunks them, generates embeddings via `sentence-transformers`, and stores them locally in a persistent `chromadb` instance.
  - `ai/intent.py`: Lightweight rule-based classification identifying the user's intent.
  - `ai/llm.py`: A robust abstraction that attempts to contact an Ollama API. If the API fails or is disabled, it gracefully degrades to a deterministic summary of the retrieved ChromaDB chunks, preventing the app from crashing during demonstrations.

### 3. Data Storage
- **ChromaDB**: Acts as the local vector database. Stored in `backend/vector_db/`.
- **Knowledge Base**: Curated text files in `backend/knowledge_base/` representing official government documentation.

## Security Considerations for Production
- **Authentication**: Replace `auth/sso.py` with an actual OAuth2/OIDC integration (e.g., Keycloak, DigiLocker Auth).
- **Vector DB**: Migrate from local ChromaDB to a managed vector database (e.g., Pinecone, Milvus, or managed PostgreSQL with pgvector).
- **Secrets Management**: Store API keys in AWS Secrets Manager or Azure Key Vault rather than `.env` files.
- **Validation**: Implement robust Pydantic input validation and sanitation on all FastAPI routes to prevent injection attacks.
