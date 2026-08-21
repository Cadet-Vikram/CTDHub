"""Authentication routes — reads SECRET_KEY from environment"""

import hashlib, uuid, os
from datetime import datetime, timedelta
from typing import Optional

import jwt
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.database import User, get_db

router  = APIRouter()
_SECRET = os.getenv("SECRET_KEY", "ctd-change-in-production-use-env-var")
_ALG    = "HS256"
oauth2  = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def _hash(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()


def _token(user_id: str, role: str) -> str:
    return jwt.encode(
        {"sub": user_id, "role": role,
         "exp": datetime.utcnow() + timedelta(hours=24)},
        _SECRET, algorithm=_ALG,
    )


class RegisterBody(BaseModel):
    email: str
    password: str
    full_name: str
    role: str = "volunteer"


@router.post("/register")
async def register(body: RegisterBody, db: AsyncSession = Depends(get_db)):
    if (await db.execute(select(User).where(User.email == body.email))).scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(id=str(uuid.uuid4()), email=body.email,
                hashed_password=_hash(body.password),
                full_name=body.full_name, role=body.role)
    db.add(user)
    await db.commit()
    return {"access_token": _token(user.id, user.role),
            "token_type": "bearer", "role": user.role}


@router.post("/login")
async def login(form: OAuth2PasswordRequestForm = Depends(),
                db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == form.username))
    user   = result.scalar_one_or_none()
    if not user or user.hashed_password != _hash(form.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"access_token": _token(user.id, user.role),
            "token_type": "bearer", "role": user.role}
