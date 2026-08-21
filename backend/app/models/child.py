"""
Child database model - stores missing and found children records
"""

from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text, JSON
from sqlalchemy.sql import func
import uuid
from app.database import Base


class Child(Base):
    __tablename__ = "children"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False)
    age = Column(Integer, nullable=False)
    gender = Column(String(10))
    status = Column(String(20), default="missing")  # missing | found | closed

    # Physical description
    height_cm = Column(Float)
    weight_kg = Column(Float)
    eye_color = Column(String(30))
    hair_color = Column(String(30))
    skin_tone = Column(String(30))
    identifying_marks = Column(Text)

    # Last seen info
    last_seen_location = Column(String(255))
    last_seen_lat = Column(Float)
    last_seen_lng = Column(Float)
    last_seen_date = Column(DateTime)

    # Contact
    guardian_name = Column(String(100))
    guardian_phone = Column(String(20))
    guardian_email = Column(String(100))

    # Aadhaar (hashed, never store raw)
    aadhaar_hash = Column(String(64))
    aadhaar_verified = Column(Boolean, default=False)

    # Biometric - below 5 years flag
    has_biometrics = Column(Boolean, default=True)
    too_young_for_biometrics = Column(Boolean, default=False)

    # Face embedding vector stored as JSON list
    face_embedding = Column(JSON)
    face_image_path = Column(String(255))

    # Age-progressed image path (GAN-generated)
    age_progressed_image_path = Column(String(255))
    age_at_progression = Column(Integer)

    # Metadata
    reported_by = Column(String(100))
    police_station = Column(String(200))
    fir_number = Column(String(50))
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    notes = Column(Text)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "age": self.age,
            "gender": self.gender,
            "status": self.status,
            "last_seen_location": self.last_seen_location,
            "last_seen_lat": self.last_seen_lat,
            "last_seen_lng": self.last_seen_lng,
            "last_seen_date": str(self.last_seen_date) if self.last_seen_date else None,
            "guardian_name": self.guardian_name,
            "guardian_phone": self.guardian_phone,
            "face_image_path": self.face_image_path,
            "age_progressed_image_path": self.age_progressed_image_path,
            "has_biometrics": self.has_biometrics,
            "too_young_for_biometrics": self.too_young_for_biometrics,
            "aadhaar_verified": self.aadhaar_verified,
            "police_station": self.police_station,
            "fir_number": self.fir_number,
            "created_at": str(self.created_at) if self.created_at else None,
            "notes": self.notes,
        }
