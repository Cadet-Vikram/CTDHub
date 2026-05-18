"""
/api/auth — JWT authentication endpoints.
"""
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from jose import jwt

SECRET_KEY = "change-me-in-production"
ALGORITHM = "HS256"
EXPIRE_MINUTES = 60

router = APIRouter()

# Prototype user store (use DB in production)
USERS = {
    "admin@ctd.gov.in": {"password": "admin123", "role": "admin", "name": "Admin User"},
    "officer@police.gov.in": {"password": "officer123", "role": "authority", "name": "Inspector Sharma"},
    "volunteer@ctd.org": {"password": "vol123", "role": "volunteer", "name": "Priya Volunteer"},
}


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str
    role: str
    name: str


@router.post("/login", response_model=TokenOut)
def login(req: LoginRequest):
    user = USERS.get(req.email)
    if not user or user["password"] != req.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    payload = {
        "sub": req.email,
        "role": user["role"],
        "name": user["name"],
        "exp": datetime.utcnow() + timedelta(minutes=EXPIRE_MINUTES),
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return TokenOut(access_token=token, token_type="bearer", role=user["role"], name=user["name"])


@router.get("/me")
def me(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return {"email": payload["sub"], "role": payload["role"], "name": payload["name"]}
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")
