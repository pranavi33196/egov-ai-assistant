import os
import requests

CAPTCHA_PROVIDER = os.getenv("CAPTCHA_PROVIDER", "turnstile")
TURNSTILE_SECRET = os.getenv("CLOUDFLARE_TURNSTILE_SECRET", "")
RECAPTCHA_SECRET = os.getenv("RECAPTCHA_SECRET_KEY", "")


def is_captcha_configured() -> bool:
    if CAPTCHA_PROVIDER == "turnstile":
        return bool(TURNSTILE_SECRET)
    elif CAPTCHA_PROVIDER == "recaptcha":
        return bool(RECAPTCHA_SECRET)
    return False


def verify_captcha(token: str, ip: str = None) -> tuple:
    """
    Verify CAPTCHA token. Returns (success: bool, message: str).
    If not configured, allows through in dev mode with a warning.
    """
    if not is_captcha_configured():
        print("WARNING: CAPTCHA not configured — allowing request in development mode.")
        return True, "captcha_not_configured_dev_mode"

    if not token:
        return False, "CAPTCHA token is required."

    try:
        if CAPTCHA_PROVIDER == "turnstile":
            resp = requests.post(
                "https://challenges.cloudflare.com/turnstile/v0/siteverify",
                data={"secret": TURNSTILE_SECRET, "response": token, "remoteip": ip or ""},
                timeout=5
            )
            data = resp.json()
            if data.get("success"):
                return True, "verified"
            return False, f"CAPTCHA failed: {', '.join(data.get('error-codes', ['unknown']))}"

        elif CAPTCHA_PROVIDER == "recaptcha":
            resp = requests.post(
                "https://www.google.com/recaptcha/api/siteverify",
                data={"secret": RECAPTCHA_SECRET, "response": token, "remoteip": ip or ""},
                timeout=5
            )
            data = resp.json()
            if data.get("success"):
                return True, "verified"
            return False, "reCAPTCHA verification failed."

    except Exception as e:
        return False, f"CAPTCHA service error: {str(e)}"

    return False, "Unknown CAPTCHA provider."
