"""
Database Models - SQLAlchemy + Async SQLite (swap to PostgreSQL for production)
"""

import json
import datetime
from typing import Optional, List
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, LargeBinary
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = "sqlite+aiosqlite:///./connecting_dots.db"

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()


class ChildRecord(Base):
    __tablename__ = "children"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(String(50), unique=True, index=True)
    name = Column(String(200), nullable=False)
    age_at_disappearance = Column(Integer)
    date_of_birth = Column(String(20))
    gender = Column(String(20))
    missing_since = Column(DateTime, default=datetime.datetime.utcnow)
    last_seen_location = Column(String(500))
    last_seen_lat = Column(Float)
    last_seen_lon = Column(Float)
    aadhaar_number = Column(String(20), nullable=True)  # hashed
    guardian_name = Column(String(200))
    guardian_phone = Column(String(20))
    guardian_email = Column(String(200))
    description = Column(Text)
    status = Column(String(50), default="missing")  # missing, found, closed
    photo_path = Column(String(500))
    face_embedding = Column(Text, nullable=True)  # JSON-encoded float list
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    is_under_5 = Column(Boolean, default=False)
    distinctive_features = Column(Text)
    police_case_number = Column(String(100))
    district = Column(String(100))
    state = Column(String(100))

    def get_embedding(self) -> Optional[List[float]]:
        if self.face_embedding:
            return json.loads(self.face_embedding)
        return None

    def set_embedding(self, embedding: List[float]):
        self.face_embedding = json.dumps(embedding)


class SightingReport(Base):
    __tablename__ = "sightings"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(String(50), index=True)
    reporter_name = Column(String(200))
    reporter_phone = Column(String(20))
    sighting_lat = Column(Float)
    sighting_lon = Column(Float)
    sighting_location = Column(String(500))
    sighting_time = Column(DateTime)
    confidence_score = Column(Float)
    photo_path = Column(String(500))
    description = Column(Text)
    verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class AlertLog(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(String(50), index=True)
    alert_type = Column(String(50))  # SOS, match_found, sighting
    message = Column(Text)
    recipients = Column(Text)  # JSON list
    sent_at = Column(DateTime, default=datetime.datetime.utcnow)
    status = Column(String(50), default="sent")
    lat = Column(Float, nullable=True)
    lon = Column(Float, nullable=True)


class AgeProgressionRecord(Base):
    __tablename__ = "age_progressions"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(String(50), index=True)
    original_photo = Column(String(500))
    progressed_photo = Column(String(500))
    original_age = Column(Integer)
    target_age = Column(Integer)
    years_progressed = Column(Integer)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
