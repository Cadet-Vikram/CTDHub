"""Alert model"""
from sqlalchemy import Column, String, Float, Boolean, DateTime, Text, JSON
from sqlalchemy.sql import func
import uuid
from app.database import Base


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    child_id = Column(String, nullable=False)
    child_name = Column(String(100))
    alert_type = Column(String(30))  # sos | match_found | sighting | amber
    severity = Column(String(10), default="high")  # low | medium | high | critical
    message = Column(Text)
    location = Column(String(255))
    lat = Column(Float)
    lng = Column(Float)
    radius_km = Column(Float, default=10.0)
    sent_to = Column(JSON)  # list of authority IDs/phone numbers notified
    acknowledged = Column(Boolean, default=False)
    resolved = Column(Boolean, default=False)
    match_confidence = Column(Float)
    created_at = Column(DateTime, server_default=func.now())

    def to_dict(self):
        return {
            "id": self.id,
            "child_id": self.child_id,
            "child_name": self.child_name,
            "alert_type": self.alert_type,
            "severity": self.severity,
            "message": self.message,
            "location": self.location,
            "lat": self.lat,
            "lng": self.lng,
            "radius_km": self.radius_km,
            "acknowledged": self.acknowledged,
            "resolved": self.resolved,
            "match_confidence": self.match_confidence,
            "created_at": str(self.created_at) if self.created_at else None,
        }
