import re

# Specific government service categories
SERVICE_INTENTS = {
    "RATION_CARD": ["ration card", "ration", "pds", "rice card", "food security", "fair price", "nfsa", "rashan", "rationcard"],
    "AADHAAR": ["aadhaar", "uidai", "aadhar", "uid", "biometric", "update address", "myaadhaar", "eaadhaar", "aadhar card", "aadhaar card"],
    "PAN_CARD": ["pan card", "pan", "nsdl", "utiitsl", "income tax number", "e-pan", "form 49a", "pancard"],
    "VOTER_ID": ["voter id", "voter", "epic", "election card", "nvsp", "eci", "form 6", "voter card", "voter registration"],
    "AYUSHMAN_BHARAT": ["ayushman", "pmjay", "golden card", "health card", "5 lakh insurance", "ayushman bharat", "pm jay"],
    "PM_KISAN": ["pm kisan", "pm-kisan", "kisan samman", "farmer 6000", "dbt kisan", "pmkisan"],
    "EPFO_PF": ["epfo", "provident fund", "uan", "pf withdrawal", "form 19", "form 31", "passbook epf", "epf balance", "pf claim"],
    "PASSPORT": ["passport", "psk", "passport seva", "travel document", "tatkaal", "tatkal passport"],
    "DRIVING_LICENSE": ["driving license", "driving licence", "rto", "learner license", "sarathi", "parivahan", "dl", "driver license"],
    "PENSION": ["pension", "widow pension", "old age pension", "oap", "divyang", "senior citizen pension", "viklang pension"],
    "SCHOLARSHIP": ["scholarship", "nsp", "student aid", "education fund", "stipend", "post matric", "pre matric", "scholarships"],
    "BIRTH_CERTIFICATE": ["birth certificate", "dob certificate", "birth registration", "crsorgi", "birth proof"],
    "INCOME_CERTIFICATE": ["income certificate", "salary proof", "revenue certificate", "income proof", "aadhayam"],
}

# Conversational & Sub-topic Intents
TOPIC_INTENTS = {
    "DOCUMENTS_QUERY": [
        "documents", "document", "papers", "paper", "pathralu", "patralu", "dastavej", "kaagaz", 
        "proof required", "what documents", "which documents", "required documents", "documents needed",
        "certificate required", "id proof", "address proof"
    ],
    "PROCEDURE_QUERY": [
        "procedure", "how to apply", "steps", "process", "application process", "step by step",
        "ela apply cheyali", "kaise kare", "apply online", "apply offline", "registration steps", "how to get"
    ],
    "FEES_QUERY": [
        "fee", "fees", "charges", "cost", "price", "how much fee", "dabbulu", "charges required",
        "application fee", "payment", "rupees", "rs"
    ],
    "ELIGIBILITY_QUERY": [
        "eligibility", "eligible", "who can apply", "arhata", "yogyata", "qualify", "criteria", "who is eligible"
    ],
    "PORTAL_QUERY": [
        "portal", "website", "online link", "official link", "helpline", "toll free", "phone number", "contact"
    ],
    "GREETING": [
        "hello", "hi", "namaste", "namaskaram", "vanakkam", "good morning", "good evening", "good afternoon", "hey", "hii"
    ],
    "HELP_GUIDE": [
        "help", "what can you do", "services list", "guide me", "how to use", "options", "commands"
    ]
}

ALL_INTENTS = {**SERVICE_INTENTS, **TOPIC_INTENTS}


def detect_intent(query: str) -> dict:
    """
    Classifies citizen intent using strict word-boundary matching to prevent false positives.
    Returns: {"intent": str, "service": Optional[str], "confidence": float}
    """
    q_lower = query.lower().strip()
    words = re.findall(r'\b\w+\b', q_lower)

    # 1. Pure Greeting check (only if query is 1-3 greeting words)
    greet_matches = [w for w in words if w in ["hello", "hi", "namaste", "namaskaram", "vanakkam", "hey", "hii"]]
    if greet_matches and len(words) <= 3 and not any(k in q_lower for k in ["card", "aadhaar", "pan", "passport", "ration", "license", "apply"]):
        return {
            "intent": "GREETING",
            "service": None,
            "confidence": 0.95
        }

    detected_service = None
    best_service_score = 0.0

    # 2. Match Service Intents
    for service, keywords in SERVICE_INTENTS.items():
        score = 0.0
        for kw in keywords:
            if re.search(r'\b' + re.escape(kw) + r'\b', q_lower):
                score += (3.0 if " " in kw else 2.0)
        if score > best_service_score:
            best_service_score = score
            detected_service = service

    # 3. Match Topic Intents (e.g. documents, fees, procedure, eligibility)
    detected_topic = None
    best_topic_score = 0.0
    for topic, keywords in TOPIC_INTENTS.items():
        if topic in ("GREETING", "HELP_GUIDE"):
            continue
        score = 0.0
        for kw in keywords:
            if re.search(r'\b' + re.escape(kw) + r'\b', q_lower):
                score += (2.5 if " " in kw else 1.5)
        if score > best_topic_score:
            best_topic_score = score
            detected_topic = topic

    # Determine primary intent label for display
    if detected_service:
        primary_intent = detected_service
        confidence = min(0.98, 0.70 + (best_service_score * 0.1))
    elif detected_topic:
        primary_intent = detected_topic
        confidence = min(0.95, 0.65 + (best_topic_score * 0.1))
    else:
        primary_intent = "GENERAL_GOVERNMENT_QUERY"
        confidence = 0.60

    return {
        "intent": primary_intent,
        "service": detected_service,
        "topic": detected_topic,
        "confidence": round(confidence, 2)
    }
