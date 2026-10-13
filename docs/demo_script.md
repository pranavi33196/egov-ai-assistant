# Company Demo Script

## 1. Setup Phase
- Ensure the FastAPI backend is running (`uvicorn main:app --reload --port 8000`).
- Ensure the React frontend is running (`npm run dev`).
- Open `http://localhost:5173` in a web browser.
- Verify the system is in MOCK mode or REAL mode as intended via the backend `.env`.

## 2. Introduction
*"Welcome to the e-Gov AI Assistant. This prototype demonstrates a complete flow for multilingual citizen queries, using a retrieval-augmented generation (RAG) pipeline to prevent hallucination, and a BHASHINI integration layer to handle language translation and voice capabilities."*

## 3. Login
- Display the Login screen.
- Emphasize the "Prototype SSO" label.
- Enter credentials:
  - **Username**: `demo`
  - **Password**: `demo123`
- Click "Login with SSO".
- *"The system authenticates the citizen and issues a secure token, directing them to their personalized dashboard."*

## 4. The Dashboard & System Status
- Highlight the **System Status** panel on the right.
- Note the indicators showing Backend, RAG Engine, ChromaDB, BHASHINI, and AI Engine status.
- *"Notice the system dynamically checks the health of our services. Currently, we are operating in [Mock/Real] mode for language translation, and our AI Engine is using [Ollama/Fallback] to generate answers."*

## 5. English Query Execution
- Click the sample query: *"How can I apply for a ration card?"*
- Click **Ask Assistant**.
- Discuss the output:
  - The AI Answer is generated.
  - The Intent is detected as `RATION CARD` with a confidence score.
  - The exact Government Source used to answer the question is displayed.
- *"This answer isn't generated from general web data; it's grounded directly in our official Government Knowledge Base."*

## 6. Multilingual Translation (Telugu)
- Change the language selector to **Telugu**.
- Click the sample query: *"రేషన్ కార్డు కోసం ఎలా దరఖాస్తు చేయాలి?"*
- Click **Ask Assistant**.
- *"The assistant translates the query, processes the intent, retrieves the English knowledge base documents, generates the answer, and translates it back—all seamlessly."*

## 7. Voice Interaction (TTS)
- Point to the **Listen** button on the response.
- Click the button to demonstrate the Text-to-Speech capability (via BHASHINI or Browser fallback).
- *"Citizens who may have difficulty reading can simply listen to the instructions in their native language."*

## 8. Closing
- Highlight the disclaimer at the bottom right.
- Discuss how the modular architecture allows swapping the Prototype SSO for DigiLocker, the Mock BHASHINI layer for real API credentials, and the local RAG engine for a larger distributed database.
- Conclude the demo and take questions.
