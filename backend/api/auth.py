from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional
from auth.sso import authenticate_user, create_access_token

router = APIRouter()

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str

class UserProfile(BaseModel):
    name: str
    role: str

@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest):
    user = authenticate_user(request.username, request.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials or Prototype SSO not configured for this user",
        )
    access_token = create_access_token(data={"sub": user["username"], "name": user["name"], "role": user["role"]})
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=UserProfile)
def get_me():
    # In a real app we would depend on a token verification dependency
    # For MVP, we return a mock response or require the frontend to just decode the JWT
    return UserProfile(name="Demo Citizen", role="citizen")
