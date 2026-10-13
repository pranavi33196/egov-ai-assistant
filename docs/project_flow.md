# Project Flow

## 1. User Access & Authentication
1. User navigates to the application URL.
2. User is presented with a prototype SSO login screen.
3. User enters credentials (e.g. demo / demo123).
4. The system issues a JWT token.
5. The application stores the token and redirects to the Dashboard.

## 2. Setting Preferences
1. The dashboard loads.
2. The user's information is fetched via `/api/auth/me`.
3. The system status is retrieved via `/api/health`.
4. User selects a preferred language from the Language Selector (English, Telugu, Hindi).

## 3. Asking a Question (Text or Voice)
1. User types a query or clicks the Microphone to record audio.
2. If Voice: Audio is processed via the `/api/speech-to-text` endpoint (or web fallback in mock mode).
3. The frontend submits the query along with the selected language to `/api/query`.

## 4. Backend Query Pipeline
1. **Translation**: The `bhashini` adapter translates the query to English (canonical language).
2. **Intent Detection**: The English query is matched against intent rules (e.g., RATION_CARD, PASSPORT) and assigned a confidence score.
3. **RAG Retrieval**: The English query is embedded via `sentence-transformers` and searched in `chromadb` against the Government Knowledge Base.
4. **LLM Generation**:
   - The system checks if `Ollama` is available.
   - If available, it prompts the LLM to generate an answer solely based on the retrieved context.
   - If unavailable, the system generates a deterministic summary of the top context chunk.
5. **Reverse Translation**: The generated answer is translated back to the user's selected language via the `bhashini` adapter.
6. **Response**: The final answer, intent metadata, and source URLs/titles are returned to the frontend.

## 5. UI Presentation & Text-to-Speech
1. The frontend displays the AI Answer, Intent, Confidence, and Sources.
2. The UI animates and highlights the information clearly.
3. The user can click the "Listen" button.
4. The frontend either invokes the `/api/text-to-speech` endpoint (real mode) or uses the Browser SpeechSynthesis API (mock mode) to read the answer aloud.
