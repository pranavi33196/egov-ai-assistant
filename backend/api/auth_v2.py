from fastapi import APIRouter, Depends, HTTPException, status, Request, BackgroundTasks
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional
import os
import time

# Load environment variables from .env before anything else
try:
    from dotenv import load_dotenv
    import pathlib
    load_dotenv(dotenv_path=pathlib.Path(__file__).parent.parent / ".env")
except ImportError:
    pass

from database.base import get_db
from database.models import User
from auth.security import (
    hash_password, verify_password, create_access_token,
    generate_otp, create_otp_record, validate_otp, log_security_event,
    check_resend_cooldown, OTP_RESEND_COOLDOWN
)
from auth.email_service import (
    send_registration_otp, send_login_otp, send_password_reset_otp,
    is_email_configured, smtp_health_check
)
from auth.captcha import verify_captcha
from auth.dependencies import get_current_user

router = APIRouter()

# ── Simple in-memory rate limiter ─────────────────────────────────────────────
_rate_store: dict = {}

def check_rate_limit(key: str, max_attempts: int = 5, window: int = 300) -> bool:
    now = time.time()
    _rate_store[key] = [t for t in _rate_store.get(key, []) if now - t < window]
    if len(_rate_store[key]) >= max_attempts:
        return False
    _rate_store[key].append(now)
    return True


# ── Schemas ───────────────────────────────────────────────────────────────────
class RegisterRequest(BaseModel):
    full_name: str
    email: str
    password: str
    confirm_password: str
    captcha_token: Optional[str] = None

class VerifyOTPRequest(BaseModel):
    email: str
    otp: str
    purpose: str

class ResendOTPRequest(BaseModel):
    email: str
    purpose: str

class LoginRequest(BaseModel):
    email: str  # Supports email or username
    password: str
    captcha_token: Optional[str] = None

class Login2FARequest(BaseModel):
    email: str
    otp: str

class ForgotPasswordRequest(BaseModel):
    email: str
    captcha_token: Optional[str] = None

class ResetPasswordRequest(BaseModel):
    email: str
    otp: str
    new_password: str

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

class UpdateProfileRequest(BaseModel):
    full_name: Optional[str] = None
    preferred_language: Optional[str] = None


def find_user_by_identifier(db: Session, identifier: str) -> Optional[User]:
    cleaned = identifier.strip()
    if not cleaned:
        return None
    # 1. Exact email match
    user = db.query(User).filter(User.email == cleaned).first()
    if user:
        return user
    # 2. Case-insensitive email prefix or full name match
    user = db.query(User).filter(
        or_(
            User.email.ilike(cleaned),
            User.email.ilike(f"{cleaned}@%"),
            User.full_name.ilike(cleaned)
        )
    ).first()
    return user


# ── REGISTER ──────────────────────────────────────────────────────────────────
@router.post("/register")
def register(req: RegisterRequest, background_tasks: BackgroundTasks,
             request: Request, db: Session = Depends(get_db)):
    ip = request.client.host if request.client else None

    if not check_rate_limit(f"register:{ip}", 10, 3600):
        raise HTTPException(status_code=429, detail="Too many registration attempts. Please try again later.")

    captcha_ok, _ = verify_captcha(req.captcha_token, ip)
    if not captcha_ok:
        raise HTTPException(status_code=400, detail="CAPTCHA verification failed.")

    if req.password != req.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match.")
    if len(req.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters.")

    email_val = req.email.strip()
    if "@" not in email_val:
        email_val = f"{email_val}@citizen.gov.in"

    if db.query(User).filter(User.email == email_val).first():
        raise HTTPException(status_code=400, detail="An account with this email/username already exists.")

    user = User(
        full_name=req.full_name.strip(), email=email_val,
        hashed_password=hash_password(req.password),
        role="citizen", is_active=False, is_email_verified=False, auth_provider="email"
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    otp = generate_otp()
    create_otp_record(db, user.id, "register", otp)

    if is_email_configured():
        background_tasks.add_task(send_registration_otp, user.email, otp, user.full_name)
        return {
            "message": f"Account created. A 6-digit verification code has been sent to {user.email}. Check your inbox (including spam).",
            "email_sent": True,
            "registered_email": user.email
        }
    else:
        # Dev mode: return OTP in response so testing works without SMTP
        return {
            "message": "Account created. Email service not configured — check server console for OTP.",
            "email_sent": False,
            "dev_otp": otp,
            "registered_email": user.email
        }


# ── VERIFY OTP ────────────────────────────────────────────────────────────────
@router.post("/verify-otp")
def verify_otp_endpoint(req: VerifyOTPRequest, db: Session = Depends(get_db)):
    user = find_user_by_identifier(db, req.email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    ok, msg = validate_otp(db, user.id, req.purpose, req.otp)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)

    if req.purpose == "register":
        user.is_active = True
        user.is_email_verified = True
        db.commit()
        return {"message": "Email verified. You can now log in."}

    return {"message": msg}


# ── RESEND OTP ────────────────────────────────────────────────────────────────
@router.post("/resend-otp")
def resend_otp(req: ResendOTPRequest, background_tasks: BackgroundTasks,
               request: Request, db: Session = Depends(get_db)):
    user = find_user_by_identifier(db, req.email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    # Enforce 30-second resend cooldown
    can_resend, wait_secs = check_resend_cooldown(db, user.id, req.purpose)
    if not can_resend:
        raise HTTPException(
            status_code=429,
            detail=f"Please wait {wait_secs} seconds before requesting a new code."
        )

    otp = generate_otp()
    create_otp_record(db, user.id, req.purpose, otp)

    if is_email_configured():
        if req.purpose == "register":
            background_tasks.add_task(send_registration_otp, user.email, otp, user.full_name)
        elif req.purpose == "login_2fa":
            background_tasks.add_task(send_login_otp, user.email, otp, user.full_name)
        else:
            background_tasks.add_task(send_password_reset_otp, user.email, otp, user.full_name)
        return {"message": f"New verification code sent to {user.email}."}
    else:
        return {"message": "Email not configured. Check server console for OTP.", "dev_otp": otp}


# ── LOGIN (step 1 — credentials) ──────────────────────────────────────────────
@router.post("/login")
def login(req: LoginRequest, background_tasks: BackgroundTasks,
          request: Request, db: Session = Depends(get_db)):
    ip = request.client.host if request.client else None

    if not check_rate_limit(f"login:{ip}", 10, 300):
        raise HTTPException(status_code=429, detail="Too many login attempts. Please wait 5 minutes.")

    captcha_ok, _ = verify_captcha(req.captcha_token, ip)
    if not captcha_ok:
        raise HTTPException(status_code=400, detail="CAPTCHA verification failed.")

    user = find_user_by_identifier(db, req.email)
    if not user or not user.hashed_password:
        log_security_event(db, None, "login_fail", f"Unknown identifier: {req.email}", ip)
        raise HTTPException(status_code=401, detail="Invalid username/email or password.")

    if not verify_password(req.password, user.hashed_password):
        log_security_event(db, user.id, "login_fail", "Incorrect password", ip)
        raise HTTPException(status_code=401, detail="Invalid username/email or password.")

    if not user.is_active or not user.is_email_verified:
        raise HTTPException(status_code=403,
            detail="Account not verified. Please check your verification code.")

    # Send 2FA OTP to the user's OWN registered email
    otp = generate_otp()
    create_otp_record(db, user.id, "login_2fa", otp)

    if is_email_configured():
        background_tasks.add_task(send_login_otp, user.email, otp, user.full_name)
        return {
            "message": f"A verification code has been sent to {user.email}.",
            "requires_2fa": True,
            "email_sent": True,
            "email": user.email
        }
    else:
        return {
            "message": "Email not configured. Check server console for 2FA code.",
            "requires_2fa": True,
            "email_sent": False,
            "dev_otp": otp,
            "email": user.email
        }


# ── LOGIN (step 2 — 2FA verify) ───────────────────────────────────────────────
@router.post("/login/verify-2fa")
def verify_2fa(req: Login2FARequest, db: Session = Depends(get_db)):
    user = find_user_by_identifier(db, req.email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    ok, msg = validate_otp(db, user.id, "login_2fa", req.otp)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)

    token = create_access_token({
        "sub": str(user.id), "email": user.email,
        "role": user.role, "name": user.full_name
    })
    return {"access_token": token, "token_type": "bearer"}


# ── INSTANT DEMO LOGIN (Direct Access) ───────────────────────────────────────
@router.post("/demo-login")
def demo_login(db: Session = Depends(get_db)):
    demo_email = "pranavi@citizen.gov.in"
    user = db.query(User).filter(User.email == demo_email).first()
    if not user:
        user = User(
            full_name="Pranavi",
            email=demo_email,
            hashed_password=hash_password("DemoPassword123!"),
            role="citizen",
            is_active=True,
            is_email_verified=True,
            preferred_language="te"
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        user.is_active = True
        user.is_email_verified = True
        db.commit()

    token = create_access_token({
        "sub": str(user.id),
        "email": user.email,
        "role": user.role,
        "name": user.full_name
    })
    return {"access_token": token, "token_type": "bearer", "user": {"full_name": user.full_name, "email": user.email}}


# ── FORGOT PASSWORD ───────────────────────────────────────────────────────────
@router.post("/forgot-password")
def forgot_password(req: ForgotPasswordRequest, background_tasks: BackgroundTasks,
                    request: Request, db: Session = Depends(get_db)):
    ip = request.client.host if request.client else None
    verify_captcha(req.captcha_token, ip)

    user = find_user_by_identifier(db, req.email)
    if user:
        otp = generate_otp()
        create_otp_record(db, user.id, "password_reset", otp)
        if is_email_configured():
            background_tasks.add_task(send_password_reset_otp, user.email, otp, user.full_name)
        else:
            # Dev mode only — never in production
            pass  # OTP available via /api/auth/smtp-health or check DB

    return {
        "message": "If an account with that email exists, a reset code has been sent.",
        "email_sent": is_email_configured()
    }


# ── RESET PASSWORD ────────────────────────────────────────────────────────────
@router.post("/reset-password")
def reset_password(req: ResetPasswordRequest, db: Session = Depends(get_db)):
    user = find_user_by_identifier(db, req.email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    ok, msg = validate_otp(db, user.id, "password_reset", req.otp)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)

    if len(req.new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters.")

    user.hashed_password = hash_password(req.new_password)
    db.commit()
    return {"message": "Password reset successfully. You can now log in."}


# ── ME ────────────────────────────────────────────────────────────────────────
@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "full_name": current_user.full_name,
        "email": current_user.email,
        "role": current_user.role,
        "preferred_language": current_user.preferred_language,
        "auth_provider": current_user.auth_provider,
        "is_email_verified": current_user.is_email_verified,
        "avatar_url": current_user.avatar_url,
        "created_at": current_user.created_at.isoformat() if current_user.created_at else None
    }


# ── UPDATE PROFILE ────────────────────────────────────────────────────────────
@router.put("/profile")
def update_profile(req: UpdateProfileRequest, current_user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == current_user.id).first()
    if req.full_name:
        user.full_name = req.full_name
    if req.preferred_language and req.preferred_language in ["en", "te", "hi"]:
        user.preferred_language = req.preferred_language
    db.commit()
    return {"message": "Profile updated."}


# ── CHANGE PASSWORD ───────────────────────────────────────────────────────────
@router.post("/change-password")
def change_password(req: ChangePasswordRequest, current_user: User = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == current_user.id).first()
    if not user.hashed_password:
        raise HTTPException(status_code=400, detail="OAuth accounts cannot change password here.")
    if not verify_password(req.current_password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Current password is incorrect.")
    if len(req.new_password) < 8:
        raise HTTPException(status_code=400, detail="New password must be at least 8 characters.")
    user.hashed_password = hash_password(req.new_password)
    db.commit()
    return {"message": "Password changed successfully."}
