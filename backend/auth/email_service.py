"""
Secure Gmail SMTP email service for e-Gov AI Assistant.

Security rules enforced:
- Credentials are ONLY loaded from environment variables (via python-dotenv).
- SMTP_PASSWORD is NEVER printed, logged, or exposed.
- OTP values are NEVER printed or logged by this module.
- The SMTP sender is always SMTP_FROM_EMAIL (from env).
- OTP destination is always the user's own registered/entered email.
"""

import os
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Tuple

# ── Load .env FIRST (before reading any os.getenv) ─────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env'))
except ImportError:
    pass  # dotenv not installed; rely on system environment

# ── Read SMTP config from environment ONLY ──────────────────────────────────
SMTP_HOST     = os.getenv("SMTP_HOST", "").strip()
SMTP_PORT     = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "").strip()
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "").strip()
SMTP_FROM     = os.getenv("SMTP_FROM_EMAIL", "").strip()
SMTP_USE_TLS  = os.getenv("SMTP_USE_TLS", "true").strip().lower() == "true"


def is_email_configured() -> bool:
    """Returns True only when all four required SMTP variables are non-empty."""
    return bool(SMTP_HOST and SMTP_USERNAME and SMTP_PASSWORD and SMTP_FROM)


def smtp_health_check() -> Tuple[bool, str]:
    """
    Opens a real SMTP connection with EHLO + STARTTLS + AUTH and immediately
    closes it. Does NOT send an email, does NOT expose credentials in the return value.

    Returns:
        (True,  "SMTP: CONNECTED")  – connection + auth succeeded
        (False, "SMTP: NOT CONFIGURED / <reason>")  – credentials missing or auth failed
    """
    if not is_email_configured():
        missing = [
            k for k, v in {
                "SMTP_HOST": SMTP_HOST,
                "SMTP_USERNAME": SMTP_USERNAME,
                "SMTP_PASSWORD": SMTP_PASSWORD,
                "SMTP_FROM_EMAIL": SMTP_FROM,
            }.items() if not v
        ]
        return False, f"SMTP: NOT CONFIGURED – missing: {', '.join(missing)}"

    try:
        ctx = ssl.create_default_context()
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
            server.ehlo()
            if SMTP_USE_TLS:
                server.starttls(context=ctx)
                server.ehlo()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            # Immediately quit – no email sent
        return True, "SMTP: CONNECTED"
    except smtplib.SMTPAuthenticationError:
        return False, "SMTP: AUTHENTICATION FAILED – check SMTP_USERNAME and SMTP_PASSWORD"
    except smtplib.SMTPConnectError as e:
        return False, f"SMTP: CONNECTION REFUSED – {SMTP_HOST}:{SMTP_PORT}"
    except Exception as e:
        return False, f"SMTP: ERROR – {type(e).__name__}"


def _send_email(to_email: str, subject: str, html_body: str) -> Tuple[bool, str]:
    """
    Internal delivery function. Credentials are read from module-level constants
    (environment variables). SMTP_PASSWORD is never returned or logged.
    """
    if not is_email_configured():
        return False, "Email service not configured. Set SMTP_* variables in .env"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = f"e-Gov AI Assistant <{SMTP_FROM}>"
    msg["To"]      = to_email
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        ctx = ssl.create_default_context()
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
            server.ehlo()
            if SMTP_USE_TLS:
                server.starttls(context=ctx)
                server.ehlo()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.sendmail(SMTP_FROM, to_email, msg.as_bytes())
        return True, "Email sent successfully"
    except smtplib.SMTPAuthenticationError:
        return False, "SMTP authentication failed"
    except smtplib.SMTPRecipientsRefused:
        return False, f"Recipient rejected: {to_email}"
    except Exception as e:
        return False, f"Email delivery failed: {type(e).__name__}"


def _otp_html(user_name: str, label: str, expiry_mins: int) -> str:
    """
    Returns the OTP email HTML template WITH A PLACEHOLDER for the OTP.
    The actual OTP value is injected by each caller so this function never
    'sees' or stores the OTP itself.

    The caller MUST replace '{{OTP_CODE}}' with the real 6-digit OTP.
    """
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f0f4f8;font-family:Arial,Helvetica,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f0f4f8;padding:32px 16px;">
    <tr><td align="center">
      <table width="560" cellpadding="0" cellspacing="0"
             style="background:#ffffff;border-radius:16px;overflow:hidden;
                    box-shadow:0 4px 24px rgba(0,0,0,0.10);max-width:560px;width:100%;">

        <!-- Header -->
        <tr>
          <td style="background:#12355B;padding:32px 28px;text-align:center;">
            <table cellpadding="0" cellspacing="0" style="margin:0 auto 12px;">
              <tr>
                <td style="width:18px;background:#FF9933;height:40px;border-radius:3px 0 0 3px;"></td>
                <td style="width:18px;background:#ffffff;height:40px;"></td>
                <td style="width:18px;background:#138808;height:40px;border-radius:0 3px 3px 0;"></td>
              </tr>
            </table>
            <p style="color:#ffffff;font-size:22px;font-weight:800;margin:0 0 4px;">e-Gov AI Assistant</p>
            <p style="color:rgba(255,255,255,0.75);font-size:13px;margin:0;">Multilingual Government Services Gateway</p>
          </td>
        </tr>

        <!-- Body -->
        <tr>
          <td style="padding:36px 36px 24px;">
            <p style="color:#1a1a2e;font-size:15px;margin:0 0 8px;">Dear <strong>{user_name}</strong>,</p>
            <p style="color:#444;font-size:14px;margin:0 0 24px;">
              Your <strong>{label}</strong> verification code is:
            </p>

            <!-- OTP Box -->
            <table width="100%" cellpadding="0" cellspacing="0">
              <tr>
                <td align="center"
                    style="background:#EDF2F7;border:2px solid #CBD5E0;border-radius:12px;
                           padding:28px 20px;">
                  <span style="font-size:48px;font-weight:900;letter-spacing:14px;
                               color:#12355B;font-family:'Courier New',Courier,monospace;
                               display:block;">{{OTP_CODE}}</span>
                </td>
              </tr>
            </table>

            <!-- Expiry info -->
            <table width="100%" cellpadding="0" cellspacing="0" style="margin-top:24px;">
              <tr>
                <td style="padding:12px 16px;background:#FFFBEB;border-radius:8px;
                           border-left:4px solid #F59E0B;">
                  <p style="margin:0;color:#92400E;font-size:13px;">
                    ⏱ This code expires in <strong>{expiry_mins} minutes</strong>.
                    Maximum 5 attempts allowed.
                  </p>
                </td>
              </tr>
            </table>

            <p style="color:#6B7280;font-size:13px;margin:20px 0 0;">
              🔒 Do <strong>not</strong> share this code with anyone — including government officials.
            </p>
            <p style="color:#9CA3AF;font-size:12px;margin:12px 0 0;">
              If you did not initiate this request, please ignore this email.
              No action is needed.
            </p>
          </td>
        </tr>

        <!-- Footer -->
        <tr>
          <td style="background:#F9FAFB;padding:16px 24px;
                     border-top:1px solid #E5E7EB;text-align:center;">
            <p style="color:#9CA3AF;font-size:11px;margin:0;">
              e-Gov AI Assistant — Prototype · AI-Based Multilingual Query System<br>
              Not connected to real Government of India identity databases.
            </p>
          </td>
        </tr>

      </table>
    </td></tr>
  </table>
</body>
</html>"""


# ── Public OTP sending functions ─────────────────────────────────────────────

def send_registration_otp(to_email: str, otp: str, user_name: str = "Citizen") -> Tuple[bool, str]:
    """
    Send account registration / email verification OTP.
    OTP expires in 5 minutes.
    """
    html = _otp_html(user_name, "Account Registration", 5).replace("{{OTP_CODE}}", otp)
    subject = "e-Gov AI Assistant – Account Verification Code"
    return _send_email(to_email, subject, html)


def send_login_otp(to_email: str, otp: str, user_name: str = "Citizen") -> Tuple[bool, str]:
    """
    Send 2FA / login verification OTP.
    OTP expires in 5 minutes.
    """
    html = _otp_html(user_name, "Two-Factor Authentication (Login)", 5).replace("{{OTP_CODE}}", otp)
    subject = "e-Gov AI Assistant – Login Verification Code"
    return _send_email(to_email, subject, html)


def send_password_reset_otp(to_email: str, otp: str, user_name: str = "Citizen") -> Tuple[bool, str]:
    """
    Send password reset OTP.
    OTP expires in 5 minutes.
    """
    html = _otp_html(user_name, "Password Reset", 5).replace("{{OTP_CODE}}", otp)
    subject = "e-Gov AI Assistant – Password Reset Code"
    return _send_email(to_email, subject, html)


# ── Legacy compatibility wrapper ─────────────────────────────────────────────
def send_otp_email(to_email: str, otp: str, purpose: str, user_name: str = "Citizen") -> Tuple[bool, str]:
    """
    Unified dispatcher — routes to the correct typed function based on purpose.
    Kept for backward compatibility with existing background_tasks calls.
    """
    if purpose == "register":
        return send_registration_otp(to_email, otp, user_name)
    elif purpose == "login_2fa":
        return send_login_otp(to_email, otp, user_name)
    elif purpose in ("password_reset", "forgot_password"):
        return send_password_reset_otp(to_email, otp, user_name)
    else:
        html = _otp_html(user_name, "Verification", 5).replace("{{OTP_CODE}}", otp)
        return _send_email(to_email, f"e-Gov AI Assistant – Verification Code", html)
