"""
ai/llm.py  (conversational chatbot edition)

Answer generation for the e-Gov assistant.

  1. If LLM_PROVIDER is "auto" or "ollama" and an Ollama server is reachable,
     the answer is written by the local model, grounded ONLY in retrieved chunks.
  2. Otherwise, uses an intent-aware structured synthesizer that answers specific
     follow-up questions (e.g. documents, fees, procedure, eligibility) conversationally
     instead of dumping the whole document every time.
"""

import os
import re
import time
import logging
import requests

logger = logging.getLogger(__name__)

NO_CONTEXT_ANSWER = (
    "I could not find official information regarding your query in the Government Knowledge Base. "
    "Please check the National Government Services Portal at https://services.india.gov.in "
    "or visit your local citizen service center (CSC / MeeSeva)."
)

GREETING_RESPONSE = (
    "Namaste! 🙏 I am your official e-Governance AI Assistant.\n\n"
    "I can help you with citizen services including:\n"
    "• **Aadhaar Card** (Enrollment, Address Update, Biometrics)\n"
    "• **PAN Card** (New Application, Form 49A, Corrections)\n"
    "• **Ration Card** (New Card, Food Security Schemes)\n"
    "• **Voter ID (EPIC)** (Form 6 Registration, Electoral Verification)\n"
    "• **Ayushman Bharat (PM-JAY)** (5 Lakh Health Card Eligibility)\n"
    "• **PM-KISAN** (Farmer ₹6,000 Installments & DBT)\n"
    "• **EPFO PF Withdrawal** (UAN Portal, Claims, Form 19/31)\n"
    "• **Passport Services** (Tatkaal, Fresh Application at PSK)\n"
    "• **Driving License & Certificates** (Birth, Income, Pension, Scholarship)\n\n"
    "How may I assist you today?"
)

# ── Knowledge-base document parsing ──────────────────────────────────────────

_KNOWN_HEADERS = {
    "SERVICE", "DESCRIPTION", "GENERAL ELIGIBILITY", "REQUIRED DOCUMENTS",
    "APPLICATION PROCESS", "OFFICIAL PORTAL", "HELPLINE", "FEES",
    "IMPORTANT NOTES", "SOURCE / SOURCE TYPE",
}

_HEADER_RE = re.compile(r"^([A-Z][A-Z0-9 /&\-]{2,40}):\s*(.*)$")


def parse_service_doc(text: str) -> dict:
    """Return {HEADER: [lines]} for a knowledge-base .txt document."""
    fields: dict = {}
    current = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        m = _HEADER_RE.match(line)
        if m:
            name, rest = m.group(1).strip(), m.group(2).strip()
            current = name if name in _KNOWN_HEADERS else None
            if current:
                fields.setdefault(current, [])
                if rest:
                    fields[current].append(rest)
        elif current:
            fields[current].append(line)
    return fields


def _split_top_level(text: str, sep: str = ",") -> list:
    """Split on `sep` but not inside (...) or [...]"""
    items, depth, buf = [], 0, []
    for ch in text:
        if ch in "([":
            depth += 1
        elif ch in ")]":
            depth = max(0, depth - 1)
        if ch == sep and depth == 0:
            items.append("".join(buf).strip())
            buf = []
        else:
            buf.append(ch)
    tail = "".join(buf).strip()
    if tail:
        items.append(tail)
    return [i for i in items if i]


def detect_query_focus(query: str) -> str:
    """Detects whether the user is asking specifically for documents, fees, procedure, or eligibility."""
    q = query.lower()
    
    # Check greeting
    greet_words = ["hello", "hi", "namaste", "namaskaram", "vanakkam", "hey", "good morning", "good evening"]
    words = set(re.findall(r'\b\w+\b', q))
    if any(k in words for k in greet_words) and len(words) <= 3 and not any(k in q for k in ["card", "aadhaar", "pan", "passport", "ration", "license", "apply"]):
        return "GREETING"

    doc_kw = ["document", "documents", "proof", "papers", "paper", "pathralu", "patralu", "dastavej", "kaagaz", "what documents", "which documents"]
    fee_kw = ["fee", "fees", "charges", "cost", "price", "dabbulu", "how much", "rupees", "rs", "payment"]
    proc_kw = ["procedure", "how to apply", "steps", "process", "step by step", "vidhanam", "ela apply", "kaise kare", "where to apply"]
    elig_kw = ["eligibility", "eligible", "who can apply", "arhata", "yogyata", "criteria", "who is eligible"]

    if any(k in q for k in doc_kw):
        return "DOCUMENTS"
    if any(k in q for k in fee_kw):
        return "FEES"
    if any(k in q for k in proc_kw):
        return "PROCEDURE"
    if any(k in q for k in elig_kw):
        return "ELIGIBILITY"
    return "GENERAL"


# ── Rule-based Conversational Synthesizer ────────────────────────────────────

def generate_structured_synthesis(query: str, context_chunks: list) -> str:
    if not context_chunks:
        return NO_CONTEXT_ANSWER

    focus = detect_query_focus(query)
    if focus == "GREETING":
        return GREETING_RESPONSE

    f = parse_service_doc(context_chunks[0])
    if "SERVICE" not in f:
        return context_chunks[0][:800]

    def one(name: str) -> str:
        return " ".join(f.get(name, [])).strip()

    service_name = one("SERVICE") or "Citizen Service"
    portal = one("OFFICIAL PORTAL")
    helpline = one("HELPLINE")
    fees = one("FEES")
    eligibility = one("GENERAL ELIGIBILITY")
    docs = _split_top_level(one("REQUIRED DOCUMENTS"))
    steps = f.get("APPLICATION PROCESS", [])

    info_line = []
    if portal:
        info_line.append(f"Portal: {portal}")
    if helpline:
        info_line.append(f"Helpline: {helpline}")
    info_str = " | ".join(info_line)

    # 1. Targeted response for DOCUMENTS query
    if focus == "DOCUMENTS" and docs:
        out = [
            f"### 📄 Required Documents for {service_name}",
            f"To apply for or update your **{service_name}**, please prepare the following documents:\n"
        ]
        for doc in docs:
            out.append(f"• {doc}")
        if info_str:
            out.append(f"\nOfficial Access: {info_str}")
        return "\n".join(out)

    # 2. Targeted response for FEES query
    if focus == "FEES" and fees:
        out = [
            f"### 💰 Fees & Charges for {service_name}",
            f"• **Applicable Fees:** {fees}"
        ]
        if info_str:
            out.append(f"\nOfficial Access: {info_str}")
        return "\n\n".join(out)

    # 3. Targeted response for PROCEDURE query
    if focus == "PROCEDURE" and steps:
        out = [
            f"### 📝 Step-by-Step Application Procedure for {service_name}",
            "Here are the official application steps:\n"
        ]
        for s in steps:
            out.append(f"{s}")
        if info_str:
            out.append(f"\nOfficial Access: {info_str}")
        return "\n".join(out)

    # 4. Targeted response for ELIGIBILITY query
    if focus == "ELIGIBILITY" and eligibility:
        out = [
            f"### 📋 Eligibility Criteria for {service_name}",
            f"• **Who is Eligible:** {eligibility}"
        ]
        if info_str:
            out.append(f"\nOfficial Access: {info_str}")
        return "\n\n".join(out)

    # 5. Comprehensive Summary for General Queries
    out = [f"### {service_name}"]

    if one("DESCRIPTION"):
        out.append(f"Overview: {one('DESCRIPTION')}")
    if eligibility:
        out.append(f"Eligibility: {eligibility}")
    if docs:
        out.append("Required Documents: " + ", ".join(docs[:6]))
    if steps:
        out.append("Procedure:\n" + "\n".join(steps[:6]))
    if fees:
        out.append(f"Fees: {fees}")
    if one("IMPORTANT NOTES"):
        out.append(f"Note: {one('IMPORTANT NOTES')}")
    if info_str:
        out.append(f"Official Info: {info_str}")

    return "\n\n".join(out)


# ── Ollama (optional) ────────────────────────────────────────────────────────

_ollama_retry_at = 0.0

_SYSTEM_PROMPT = (
    "You are an e-Governance assistant helping Indian citizens with government services. "
    "Answer ONLY using the CONTEXT provided. Do not invent fees, dates, phone numbers, "
    "website addresses or eligibility rules. If the CONTEXT does not answer the question, "
    "say so briefly and point to https://services.india.gov.in. "
    "Write in clear, simple English (it will be translated afterwards). "
    "If the user asks a specific question (e.g. documents, fees, steps), answer that specific question directly. "
    "Plain text only, no markdown tables."
)


def _ollama_answer(query: str, chunks: list) -> str:
    base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
    model = os.getenv("OLLAMA_MODEL", "llama3")
    timeout = float(os.getenv("OLLAMA_TIMEOUT", "60"))

    context = "\n\n---\n\n".join(chunks[:2])
    resp = requests.post(
        f"{base}/api/chat",
        timeout=timeout,
        json={
            "model": model,
            "stream": False,
            "options": {"temperature": 0.2},
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": f"CONTEXT:\n{context}\n\nQUESTION:\n{query}"},
            ],
        },
    )
    resp.raise_for_status()
    text = (resp.json().get("message") or {}).get("content", "").strip()
    if not text:
        raise ValueError("empty response from Ollama")
    return text


# ── Public entry points ──────────────────────────────────────────────────────

def generate_answer_with_meta(query: str, context_chunks: list):
    """Returns (english_answer, engine) where engine is one of
    'ollama_llm', 'rag_knowledge_synthesizer', 'rag_engine'."""
    global _ollama_retry_at

    if detect_query_focus(query) == "GREETING":
        return GREETING_RESPONSE, "conversational_assistant"

    if not context_chunks:
        return NO_CONTEXT_ANSWER, "rag_engine"

    provider = os.getenv("LLM_PROVIDER", "auto").strip().lower()
    if provider in ("auto", "ollama") and time.time() >= _ollama_retry_at:
        try:
            return _ollama_answer(query, context_chunks), "ollama_llm"
        except Exception as e:
            _ollama_retry_at = time.time() + 60
            logger.warning("Ollama unavailable (%s); using rule-based synthesis for 60s.", e)

    return generate_structured_synthesis(query, context_chunks), "rag_knowledge_synthesizer"


def generate_answer(query: str, context_chunks: list) -> str:
    return generate_answer_with_meta(query, context_chunks)[0]
