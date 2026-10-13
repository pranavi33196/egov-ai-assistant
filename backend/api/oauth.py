import os
import requests
from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from urllib.parse import urlencode

from database.base import get_db
from database.models import User, OAuthAccount
from auth.security import create_access_token

router = APIRouter()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/api/oauth/google/callback")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")


def is_google_configured() -> bool:
    return bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET)


@router.get("/google/status")
def google_status():
    return {"configured": is_google_configured()}


@router.get("/google")
def google_login():
    if not is_google_configured():
        # Redirect to frontend with error rather than 503 — friendlier UX
        return RedirectResponse(url=f"{FRONTEND_URL}/login?error=google_not_configured")

    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "select_account"
    }
    auth_url = "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params)
    return RedirectResponse(url=auth_url)


@router.get("/google/callback")
def google_callback(code: str = None, error: str = None, db: Session = Depends(get_db)):
    if error or not code:
        return RedirectResponse(url=f"{FRONTEND_URL}/login?error=google_auth_failed")

    # Exchange code for tokens
    try:
        token_resp = requests.post("https://oauth2.googleapis.com/token", data={
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": GOOGLE_REDIRECT_URI
        }, timeout=10)

        if not token_resp.ok:
            return RedirectResponse(url=f"{FRONTEND_URL}/login?error=token_exchange_failed")

        tokens = token_resp.json()
        userinfo_resp = requests.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {tokens.get('access_token')}"},
            timeout=10
        )

        if not userinfo_resp.ok:
            return RedirectResponse(url=f"{FRONTEND_URL}/login?error=userinfo_failed")

        userinfo = userinfo_resp.json()
        google_id = userinfo.get("sub")
        email = userinfo.get("email")
        name = userinfo.get("name", email)
        avatar = userinfo.get("picture", "")

    except Exception as e:
        print(f"Google OAuth error: {e}")
        return RedirectResponse(url=f"{FRONTEND_URL}/login?error=google_oauth_error")

    # Find or create user
    oauth_account = db.query(OAuthAccount).filter(
        OAuthAccount.provider == "google",
        OAuthAccount.provider_user_id == google_id
    ).first()

    if oauth_account:
        user = db.query(User).filter(User.id == oauth_account.user_id).first()
    else:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            user = User(
                full_name=name, email=email,
                auth_provider="google", is_active=True,
                is_email_verified=True, avatar_url=avatar, role="citizen"
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        oauth_acc = OAuthAccount(user_id=user.id, provider="google", provider_user_id=google_id)
        db.add(oauth_acc)
        db.commit()

    token = create_access_token({
        "sub": str(user.id), "email": user.email,
        "role": user.role, "name": user.full_name
    })
    return RedirectResponse(url=f"{FRONTEND_URL}/auth/callback?token={token}")
