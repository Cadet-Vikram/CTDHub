"""User model for system authentication"""
from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.sql import func
import uuid
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(100), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100))
    role = Column(String(20), default="officer")  # admin | officer | volunteer | public
    police_station = Column(String(200))
    badge_number = Column(String(50))
    phone = Column(String(20))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
