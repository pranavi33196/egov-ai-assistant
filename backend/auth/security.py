import os
import secrets
import hashlib
import bcrypt
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from database.models import User, EmailVerification, SecurityEvent

SECRET_KEY = os.getenv("JWT_SECRET", "CHANGE_THIS_IN_PRODUCTION_KEY_32_BYTES_RANDOM")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))


def hash_password(password: str) -> str:
    # Ensure UTF-8 bytes and truncate to 72 bytes if necessary (bcrypt limitation)
    pwd_bytes = password.encode('utf-8')[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode('utf-8')


def verify_password(plain: str, hashed: str) -> bool:
    try:
        plain_bytes = plain.encode('utf-8')[:72]
        hashed_bytes = hashed.encode('utf-8')
        return bcrypt.checkpw(plain_bytes, hashed_bytes)
    except Exception:
        return False


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None


def generate_otp() -> str:
    """
    Generate a cryptographically secure 6-digit numeric OTP.
    Uses secrets.randbelow() — NOT random.choices() which is not CSPRNG.
    OTP value is NEVER logged; caller must handle securely.
    """
    return "{:06d}".format(secrets.randbelow(1_000_000))


def hash_otp(otp: str) -> str:
    return hashlib.sha256(otp.encode()).hexdigest()


def verify_otp_hash(otp: str, otp_hash: str) -> bool:
    return hashlib.sha256(otp.encode()).hexdigest() == otp_hash


OTP_EXPIRY_MINUTES = 5       # OTPs expire after 5 minutes
OTP_MAX_ATTEMPTS   = 5       # Maximum verification attempts per OTP
OTP_RESEND_COOLDOWN = 30     # Seconds before a new OTP can be requested


def create_otp_record(db: Session, user_id: int, purpose: str, otp: str,
                      expires_minutes: int = OTP_EXPIRY_MINUTES) -> EmailVerification:
    """
    Invalidates any existing active OTP for this user+purpose, then
    stores the SHA-256 hash of the new OTP. The plaintext OTP is never stored.
    """
    # Invalidate all previous active OTPs for the same user+purpose
    db.query(EmailVerification).filter(
        EmailVerification.user_id == user_id,
        EmailVerification.purpose == purpose,
        EmailVerification.is_used == False
    ).update({"is_used": True})
    db.commit()

    expires_at = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)
    record = EmailVerification(
        user_id=user_id,
        otp_hash=hash_otp(otp),   # Only the hash is stored — never the plaintext OTP
        purpose=purpose,
        expires_at=expires_at
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def check_resend_cooldown(db: Session, user_id: int, purpose: str) -> Tuple[bool, int]:
    """
    Checks whether the user must wait before requesting a new OTP.
    Returns (can_resend: bool, wait_seconds: int).
    """
    latest = db.query(EmailVerification).filter(
        EmailVerification.user_id == user_id,
        EmailVerification.purpose == purpose
    ).order_by(EmailVerification.created_at.desc()).first()

    if not latest:
        return True, 0

    created = latest.created_at
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)

    elapsed = (datetime.now(timezone.utc) - created).total_seconds()
    if elapsed < OTP_RESEND_COOLDOWN:
        wait = int(OTP_RESEND_COOLDOWN - elapsed)
        return False, wait
    return True, 0


def validate_otp(db: Session, user_id: int, purpose: str, otp: str,
                 max_attempts: int = OTP_MAX_ATTEMPTS) -> Tuple[bool, str]:
    """
    Validates a submitted OTP against the stored SHA-256 hash.
    - Enforces 5-minute expiry.
    - Enforces maximum 5 attempts.
    - Marks record as used upon success or exhaustion.
    - OTP value is compared via constant-time hash comparison.
    """
    record = db.query(EmailVerification).filter(
        EmailVerification.user_id == user_id,
        EmailVerification.purpose == purpose,
        EmailVerification.is_used == False
    ).order_by(EmailVerification.created_at.desc()).first()

    if not record:
        return False, "No active verification code found. Please request a new one."

    # Check attempt limit BEFORE expiry to prevent timing attacks
    if record.attempts >= max_attempts:
        record.is_used = True
        db.commit()
        return False, "Maximum attempts exceeded. Please request a new code."

    expires = record.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)

    if datetime.now(timezone.utc) > expires:
        record.is_used = True
        db.commit()
        return False, f"Code expired (valid for {OTP_EXPIRY_MINUTES} minutes). Please request a new one."

    # Increment attempt counter first, then verify
    record.attempts += 1
    db.commit()

    # Constant-time comparison via hash equality
    if not verify_otp_hash(otp, record.otp_hash):
        log_security_event(db, user_id, "otp_fail", f"purpose={purpose} attempt={record.attempts}")
        remaining = max_attempts - record.attempts
        if remaining <= 0:
            record.is_used = True
            db.commit()
            return False, "Maximum attempts exceeded. Please request a new code."
        return False, f"Incorrect code. {remaining} attempt(s) remaining."

    record.is_used = True
    db.commit()
    return True, "Code verified successfully."


def log_security_event(db: Session, user_id: Optional[int], event_type: str, detail: str = None, ip: str = None):
    try:
        event = SecurityEvent(user_id=user_id, event_type=event_type, detail=detail, ip_address=ip)
        db.add(event)
        db.commit()
    except Exception:
        db.rollback()
