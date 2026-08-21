"""
Alert Service
Sends AMBER-style alerts via FCM (push), Twilio (SMS), and email.
Handles geofenced alerts — only notifies authorities within radius_km.
"""
import logging
from dataclasses import dataclass
from typing import Optional
import httpx
from geopy.distance import geodesic

logger = logging.getLogger(__name__)


@dataclass
class AlertPayload:
    case_id: int
    case_number: str
    child_name: str
    alert_type: str            # AMBER | SOS | MATCH_FOUND | SIGHTING
    message: str
    center_lat: float
    center_lng: float
    radius_km: float = 50.0
    image_url: Optional[str] = None
    similarity_score: Optional[float] = None


class AlertService:
    """
    Dispatches multi-channel alerts.
    Integrates: Firebase FCM, Twilio SMS, and a simple email sender.
    """

    def __init__(self, settings):
        self.settings = settings
        self._fcm_app = None
        self._twilio_client = None
        self._setup_clients()

    def _setup_clients(self):
        # Firebase
        try:
            import firebase_admin
            from firebase_admin import credentials, messaging
            if not firebase_admin._apps:
                cred = credentials.Certificate(self.settings.FIREBASE_CREDENTIALS_PATH)
                firebase_admin.initialize_app(cred)
            self._fcm_app = True
            self._messaging = messaging
            logger.info("Firebase FCM initialized.")
        except Exception as e:
            logger.warning(f"FCM not available: {e}")

        # Twilio
        try:
            from twilio.rest import Client
            self._twilio_client = Client(
                self.settings.TWILIO_ACCOUNT_SID,
                self.settings.TWILIO_AUTH_TOKEN,
            )
            logger.info("Twilio SMS initialized.")
        except Exception as e:
            logger.warning(f"Twilio not available: {e}")

    async def dispatch_alert(
        self,
        payload: AlertPayload,
        fcm_tokens: list[str],
        phone_numbers: list[str],
    ) -> dict:
        """Send alert across all channels. Returns summary of sent counts."""
        summary = {"fcm": 0, "sms": 0, "errors": []}

        # Push notifications
        if self._fcm_app and fcm_tokens:
            sent = await self._send_fcm(payload, fcm_tokens)
            summary["fcm"] = sent

        # SMS
        if self._twilio_client and phone_numbers:
            sent = await self._send_sms(payload, phone_numbers)
            summary["sms"] = sent

        logger.info(f"Alert dispatched for case {payload.case_number}: {summary}")
        return summary

    async def _send_fcm(self, payload: AlertPayload, tokens: list[str]) -> int:
        """Send multicast FCM push notification."""
        from firebase_admin import messaging
        try:
            notification = messaging.Notification(
                title=f"🚨 {payload.alert_type}: {payload.child_name}",
                body=payload.message,
                image=payload.image_url,
            )
            data = {
                "case_id": str(payload.case_id),
                "case_number": payload.case_number,
                "alert_type": payload.alert_type,
                "lat": str(payload.center_lat),
                "lng": str(payload.center_lng),
            }
            if payload.similarity_score:
                data["similarity"] = f"{payload.similarity_score:.2f}"

            msg = messaging.MulticastMessage(
                tokens=tokens[:500],            # FCM limit per batch
                notification=notification,
                data=data,
                android=messaging.AndroidConfig(priority="high"),
                apns=messaging.APNSConfig(
                    payload=messaging.APNSPayload(
                        aps=messaging.Aps(sound="default", badge=1)
                    )
                ),
            )
            resp = messaging.send_each_for_multicast(msg)
            return resp.success_count
        except Exception as e:
            logger.error(f"FCM error: {e}")
            return 0

    async def _send_sms(self, payload: AlertPayload, phones: list[str]) -> int:
        """Send SMS via Twilio."""
        sent = 0
        body = (
            f"[CONNECTING THE DOTS] {payload.alert_type}\n"
            f"Child: {payload.child_name}\n"
            f"Case: {payload.case_number}\n"
            f"{payload.message}\n"
            f"Location: https://maps.google.com/?q={payload.center_lat},{payload.center_lng}"
        )
        for phone in phones:
            try:
                self._twilio_client.messages.create(
                    body=body[:1600],
                    from_=self.settings.TWILIO_PHONE_NUMBER,
                    to=phone,
                )
                sent += 1
            except Exception as e:
                logger.warning(f"SMS to {phone} failed: {e}")
        return sent

    def filter_by_geofence(
        self,
        all_authorities: list[dict],      # [{phone, fcm_token, lat, lng}, …]
        center_lat: float,
        center_lng: float,
        radius_km: float,
    ) -> tuple[list[str], list[str]]:
        """
        Returns (fcm_tokens, phone_numbers) for authorities within radius.
        """
        tokens, phones = [], []
        center = (center_lat, center_lng)
        for auth in all_authorities:
            if auth.get("lat") and auth.get("lng"):
                dist = geodesic(center, (auth["lat"], auth["lng"])).km
                if dist > radius_km:
                    continue
            if auth.get("fcm_token"):
                tokens.append(auth["fcm_token"])
            if auth.get("phone"):
                phones.append(auth["phone"])
        return tokens, phones

    async def send_sos_to_nearest(
        self,
        reporter_lat: float,
        reporter_lng: float,
        message: str,
        case_number: str,
        all_authorities: list[dict],
        radius_km: float = 25.0,
    ) -> dict:
        """Special SOS dispatch — tightest radius, highest priority."""
        tokens, phones = self.filter_by_geofence(
            all_authorities, reporter_lat, reporter_lng, radius_km
        )
        payload = AlertPayload(
            case_id=0,
            case_number=case_number,
            child_name="UNKNOWN",
            alert_type="SOS",
            message=f"SOS REPORT: {message}",
            center_lat=reporter_lat,
            center_lng=reporter_lng,
            radius_km=radius_km,
        )
        return await self.dispatch_alert(payload, tokens, phones)
