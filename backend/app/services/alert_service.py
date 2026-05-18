"""
Alert Service - Emergency notification system
Sends real-time alerts to:
- Police authorities (SMS via Twilio / WhatsApp)
- Nearby officers (geolocation-based)
- Push notifications (FCM)
- Email alerts
"""

import logging
import asyncio
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

# Optional integrations
try:
    from twilio.rest import Client as TwilioClient
    TWILIO_AVAILABLE = True
except ImportError:
    TWILIO_AVAILABLE = False

try:
    import firebase_admin
    from firebase_admin import messaging, credentials
    FIREBASE_AVAILABLE = False  # Set True after adding credentials
except ImportError:
    FIREBASE_AVAILABLE = False


class AlertService:
    """
    Multi-channel emergency alert dispatcher.

    Channels:
    1. SMS (Twilio)          → Police & guardian phone numbers
    2. Push Notifications    → FCM (Firebase Cloud Messaging)
    3. Email                 → SMTP
    4. Geofenced Broadcast   → Alerts officers within radius_km
    5. In-app WebSocket      → Real-time dashboard updates
    """

    def __init__(self):
        self.twilio_client = None
        self._init_twilio()
        self.connected_clients = set()  # WebSocket clients
        logger.info("AlertService initialized")

    def _init_twilio(self):
        import os
        account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        if TWILIO_AVAILABLE and account_sid and auth_token:
            self.twilio_client = TwilioClient(account_sid, auth_token)
            self.twilio_from = os.getenv("TWILIO_FROM_NUMBER", "+1234567890")
            logger.info("✅ Twilio SMS ready")

    async def send_sos_alert(
        self,
        child_id: str,
        child_name: str,
        location: str,
        lat: float,
        lng: float,
        reporter_phone: str,
        additional_info: str = "",
    ) -> dict:
        """
        Triggered by SOS button.
        Broadcasts AMBER-alert style notification to all nearby authorities.
        """
        message = (
            f"🚨 SOS ALERT - MISSING CHILD 🚨\n"
            f"Name: {child_name}\n"
            f"Location: {location}\n"
            f"GPS: {lat:.4f}, {lng:.4f}\n"
            f"Reported: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
            f"Info: {additional_info}\n"
            f"Maps: https://maps.google.com/?q={lat},{lng}\n"
            f"Case ID: {child_id}"
        )

        results = await asyncio.gather(
            self._send_sms(reporter_phone, message),
            self._broadcast_push_notification(
                title=f"🚨 AMBER ALERT: {child_name}",
                body=f"Missing child reported near {location}. Tap for details.",
                data={"child_id": child_id, "lat": str(lat), "lng": str(lng)},
            ),
            self._notify_authorities(message, lat, lng),
            return_exceptions=True,
        )

        return {
            "sos_triggered": True,
            "child_id": child_id,
            "channels_notified": ["sms", "push", "authorities"],
            "timestamp": datetime.now().isoformat(),
            "message": message,
            "results": [str(r) for r in results],
        }

    async def send_match_alert(
        self,
        child_id: str,
        child_name: str,
        confidence: float,
        match_location: str,
        guardian_phone: str,
        officer_phones: list[str],
    ) -> dict:
        """Send alert when a face match is found"""
        message = (
            f"✅ MATCH FOUND - POSSIBLE SIGHTING\n"
            f"Child: {child_name}\n"
            f"Confidence: {confidence:.1f}%\n"
            f"Location: {match_location}\n"
            f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
            f"⚠️ Please verify immediately. Case ID: {child_id}"
        )

        tasks = [self._send_sms(guardian_phone, message)]
        for phone in officer_phones:
            tasks.append(self._send_sms(phone, message))

        await asyncio.gather(*tasks, return_exceptions=True)

        return {
            "alert_type": "match_found",
            "child_id": child_id,
            "confidence": confidence,
            "notified_count": 1 + len(officer_phones),
        }

    async def _send_sms(self, phone: str, message: str) -> bool:
        """Send SMS via Twilio"""
        if self.twilio_client and phone:
            try:
                self.twilio_client.messages.create(
                    body=message,
                    from_=self.twilio_from,
                    to=phone,
                )
                logger.info(f"✅ SMS sent to {phone[:6]}****")
                return True
            except Exception as e:
                logger.error(f"SMS failed to {phone}: {e}")
        else:
            # Mock: log the alert
            logger.info(f"[MOCK SMS] To: {phone}\n{message}")
        return False

    async def _broadcast_push_notification(self, title: str, body: str, data: dict) -> bool:
        """Send FCM push notification to all registered devices"""
        if not FIREBASE_AVAILABLE:
            logger.info(f"[MOCK PUSH] {title}: {body}")
            return False
        try:
            message = messaging.Message(
                notification=messaging.Notification(title=title, body=body),
                data=data,
                topic="missing_children_alerts",
            )
            messaging.send(message)
            return True
        except Exception as e:
            logger.error(f"Push notification failed: {e}")
            return False

    async def _notify_authorities(self, message: str, lat: float, lng: float) -> int:
        """
        Notify police stations and authorities within 20km radius.
        In production: query police station DB by geolocation.
        """
        # Mock implementation — replace with real DB query
        authority_numbers = [
            "+91-100",  # Police helpline
            "+91-1098", # Childline India
        ]
        count = 0
        for phone in authority_numbers:
            if await self._send_sms(phone, message):
                count += 1
        return count

    async def register_websocket(self, websocket):
        """Register WebSocket for real-time alerts"""
        self.connected_clients.add(websocket)

    async def unregister_websocket(self, websocket):
        self.connected_clients.discard(websocket)

    async def broadcast_to_dashboard(self, alert_data: dict):
        """Broadcast alert to all connected dashboard clients"""
        import json
        dead = set()
        for client in self.connected_clients:
            try:
                await client.send_text(json.dumps(alert_data))
            except Exception:
                dead.add(client)
        self.connected_clients -= dead
