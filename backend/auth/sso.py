import os
import time
import jwt
from typing import Optional

SECRET_KEY = os.getenv("JWT_SECRET", "supersecret_demo_key")
ALGORITHM = "HS256"

def create_access_token(data: dict, expires_delta_seconds: Optional[int] = None) -> str:
    to_encode = data.copy()
    if expires_delta_seconds:
        expire = time.time() + expires_delta_seconds
    else:
        expire = time.time() + 86400  # 1 day default
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except Exception as e:
        return None

def authenticate_user(username: str, password: str) -> dict:
    # MVP Mock Authentication
    if username == "demo" and password == "demo123":
        return {"username": "demo", "name": "Demo Citizen", "role": "citizen"}
    return None
