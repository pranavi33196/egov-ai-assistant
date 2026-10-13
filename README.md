# AI-Powered Multilingual e-Governance Assistant

An AI-powered assistant that helps users access information about government services through natural-language queries in multiple languages.

## Features

- **Multilingual assistance:** Designed to support English, Telugu, and Hindi.
- **AI-powered question answering:** Uses Retrieval-Augmented Generation (RAG) to answer questions from a government-services knowledge base.
- **Semantic search:** Uses ChromaDB and Sentence Transformers to retrieve relevant information.
- **Voice interaction:** Supports speech-related features through Bhashini integration.
- **User authentication:** Includes login, registration, email OTP, Google authentication, and CAPTCHA features.
- **Conversation management:** Stores user sessions and conversation data.

## Technology Stack

### Frontend
- React
- Vite
- Tailwind CSS

### Backend
- Python
- FastAPI
- SQLite

### AI and Language Technologies
- Retrieval-Augmented Generation (RAG)
- ChromaDB
- Sentence Transformers
- Bhashini APIs

## Project Structure

```text
egov-ai-assistant/
├── backend/
│   ├── ai/
│   ├── api/
│   ├── auth/
│   ├── bhashini/
│   ├── database/
│   ├── knowledge_base/
│   ├── main.py
│   └── requirements.txt
├── frontend/
│   ├── src/
│   ├── public/
│   └── package.json
├── docs/
├── .gitignore
└── README.md
```

## Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/pranavi33196/egov-ai-assistant.git
cd egov-ai-assistant
```

### 2. Set up the backend

```bash
cd backend
python -m venv venv
```

Activate the environment on Windows:

```powershell
.\venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Configure the required environment variables using the provided `.env.example` file. Add your own credentials locally; never commit real API keys or passwords.

Start the backend using the project's configured startup command.

### 3. Set up the frontend

Open another terminal:

```bash
cd frontend
npm install
```

Configure the frontend environment variables using `frontend/.env.example`, then start the development server:

```bash
npm run dev
```

Check the project's configuration and documentation for the correct backend startup command, API URLs, and required environment variables.

## Security

- Do not commit `.env` files, API keys, passwords, or authentication secrets.
- Keep local environment files out of version control.
- Use `.env.example` files to document the required configuration without real credentials.

## Future Improvements

- Expand multilingual voice support.
- Improve retrieval accuracy and response grounding.
- Add more government-service information sources.
- Improve accessibility and user experience.

## Author

**C. Naga Pranavi**

GitHub: [pranavi33196](https://github.com/pranavi33196)