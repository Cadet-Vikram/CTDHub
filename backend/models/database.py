"""
Database models — SQLAlchemy async with SQLite (swap to PostgreSQL for production)
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text
from sqlalchemy import (
    Column, String, Integer, Float, DateTime, Boolean, Text, JSON
)
from datetime import datetime
import uuid
import os
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

# Use environment variable for production, default to SQLite for local dev
db_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./connecting_dots.db")
connect_args = {}

# Convert postgresql:// to postgresql+asyncpg:// for async support
if db_url.startswith("postgresql://") or db_url.startswith("postgres://"):
    db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)

parsed = urlsplit(db_url)
if parsed.scheme == "postgresql+asyncpg":
    query_pairs = parse_qsl(parsed.query, keep_blank_values=True)
    filtered_query = []
    for key, value in query_pairs:
        if key == "sslmode":
            if value == "require":
                connect_args["ssl"] = "require"
            continue
        if key == "channel_binding":
            continue
        filtered_query.append((key, value))
    db_url = urlunsplit(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            urlencode(filtered_query),
            parsed.fragment,
        )
    )

DATABASE_URL = db_url

engine = create_async_engine(DATABASE_URL, echo=False, connect_args=connect_args)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def _uuid():
    return str(uuid.uuid4())


class Child(Base):
    __tablename__ = "children"

    id              = Column(String,  primary_key=True, default=_uuid)
    name            = Column(String(100), nullable=False)
    age             = Column(Integer, nullable=False)
    gender          = Column(String(10), nullable=False)
    description     = Column(Text,    nullable=True)
    last_seen_location = Column(String(200), nullable=True)
    last_seen_date  = Column(DateTime, nullable=True)
    reported_by     = Column(String(100), nullable=True)
    contact_number  = Column(String(20),  nullable=True)
    aadhaar_number  = Column(String(20),  nullable=True)   # last 4 only
    status          = Column(String(20),  default="missing")  # missing|found|closed
    face_embedding  = Column(Text,    nullable=True)        # JSON float list
    photo_path      = Column(String(300), nullable=True)
    age_progressed_photo = Column(String(300), nullable=True)
    geolocation_lat = Column(Float,   nullable=True)
    geolocation_lng = Column(Float,   nullable=True)
    created_at      = Column(DateTime, default=datetime.utcnow)
    updated_at      = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    extra_data      = Column(JSON,    nullable=True)


class Alert(Base):
    __tablename__ = "alerts"

    id           = Column(String, primary_key=True, default=_uuid)
    child_id     = Column(String, nullable=False)
    alert_type   = Column(String(30), nullable=False)  # sos|match_found|broadcast
    message      = Column(Text,   nullable=False)
    sent_to      = Column(Text,   nullable=True)       # JSON list
    location_lat = Column(Float,  nullable=True)
    location_lng = Column(Float,  nullable=True)
    status       = Column(String(20), default="sent")
    created_at   = Column(DateTime,   default=datetime.utcnow)


class SearchLog(Base):
    __tablename__ = "search_logs"

    id                = Column(String, primary_key=True, default=_uuid)
    query_photo_path  = Column(String(300), nullable=False)
    matched_child_id  = Column(String, nullable=True)
    similarity_score  = Column(Float,  nullable=True)
    searched_by       = Column(String(100), nullable=True)
    location_lat      = Column(Float,  nullable=True)
    location_lng      = Column(Float,  nullable=True)
    created_at        = Column(DateTime, default=datetime.utcnow)


class User(Base):
    __tablename__ = "users"

    id              = Column(String, primary_key=True, default=_uuid)
    email           = Column(String(150), unique=True, nullable=False)
    hashed_password = Column(String(200), nullable=False)
    full_name       = Column(String(100), nullable=False)
    role            = Column(String(20),  default="volunteer")  # admin|authority|volunteer
    is_active       = Column(Boolean, default=True)
    created_at      = Column(DateTime, default=datetime.utcnow)


async def init_db():
    async with engine.begin() as conn:
        # Render boots multiple Gunicorn workers. Without a lock, they can race
        # while PostgreSQL is creating the same table/type at the same time.
        if conn.dialect.name == "postgresql":
            await conn.execute(text("SELECT pg_advisory_xact_lock(673421917)"))
        await conn.run_sync(Base.metadata.create_all, checkfirst=True)


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
