"""
Database — auto-switches between SQLite (local dev) and PostgreSQL (production).
Set DATABASE_URL environment variable on Cloud Run to use PostgreSQL.
"""

import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Column, String, Integer, Float, DateTime, Boolean, Text, JSON
from datetime import datetime
import uuid

# Auto-detect and fix DB URL format
_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./connecting_dots.db")
if _url.startswith("postgres://"):
    _url = _url.replace("postgres://", "postgresql+asyncpg://", 1)
elif _url.startswith("postgresql://") and "+asyncpg" not in _url:
    _url = _url.replace("postgresql://", "postgresql+asyncpg://", 1)

DATABASE_URL = _url
engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def _uid(): return str(uuid.uuid4())


class Child(Base):
    __tablename__ = "children"
    id                 = Column(String, primary_key=True, default=_uid)
    name               = Column(String(100), nullable=False)
    age                = Column(Integer, nullable=False)
    gender             = Column(String(10), nullable=False)
    description        = Column(Text)
    last_seen_location = Column(String(200))
    last_seen_date     = Column(DateTime)
    reported_by        = Column(String(100))
    contact_number     = Column(String(20))
    aadhaar_number     = Column(String(20))
    status             = Column(String(20), default="missing")
    face_embedding     = Column(Text)
    photo_path         = Column(String(300))
    age_progressed_photo = Column(String(300))
    geolocation_lat    = Column(Float)
    geolocation_lng    = Column(Float)
    created_at         = Column(DateTime, default=datetime.utcnow)
    updated_at         = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Alert(Base):
    __tablename__ = "alerts"
    id           = Column(String, primary_key=True, default=_uid)
    child_id     = Column(String, nullable=False)
    alert_type   = Column(String(30), nullable=False)
    message      = Column(Text, nullable=False)
    sent_to      = Column(Text)
    location_lat = Column(Float)
    location_lng = Column(Float)
    status       = Column(String(20), default="sent")
    created_at   = Column(DateTime, default=datetime.utcnow)


class SearchLog(Base):
    __tablename__ = "search_logs"
    id               = Column(String, primary_key=True, default=_uid)
    query_photo_path = Column(String(300))
    matched_child_id = Column(String)
    similarity_score = Column(Float)
    searched_by      = Column(String(100))
    location_lat     = Column(Float)
    location_lng     = Column(Float)
    created_at       = Column(DateTime, default=datetime.utcnow)


class User(Base):
    __tablename__ = "users"
    id              = Column(String, primary_key=True, default=_uid)
    email           = Column(String(150), unique=True, nullable=False)
    hashed_password = Column(String(200), nullable=False)
    full_name       = Column(String(100), nullable=False)
    role            = Column(String(20), default="volunteer")
    is_active       = Column(Boolean, default=True)
    created_at      = Column(DateTime, default=datetime.utcnow)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
