"""
Alert System
- SMS via Twilio
- Push via Firebase
- Email via SendGrid
- AMBER-alert style broadcast
"""

import os
import json
import logging
import datetime
from typing import List, Optional

logger = logging.getLogger(__name__)

TWILIO_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_FROM = os.getenv("TWILIO_PHONE", "+1234567890")
FIREBASE_KEY = os.getenv("FIREBASE_SERVER_KEY", "")
SENDGRID_KEY = os.getenv("SENDGRID_API_KEY", "")
POLICE_CONTROL_ROOM = os.getenv("POLICE_PHONE", "+911001")
CHILDLINE_NUMBER = "1098"


# ─── SMS ─────────────────────────────────────────────────────────────────────

def send_sms(to: str, message: str) -> bool:
    if not TWILIO_SID:
        logger.info(f"[MOCK SMS] To {to}: {message[:80]}...")
        return True
    try:
        from twilio.rest import Client
        client = Client(TWILIO_SID, TWILIO_TOKEN)
        msg = client.messages.create(body=message, from_=TWILIO_FROM, to=to)
        logger.info(f"SMS sent: {msg.sid}")
        return True
    except Exception as e:
        logger.error(f"SMS error: {e}")
        return False


# ─── Push Notifications ───────────────────────────────────────────────────────

def send_push_notification(token: str, title: str, body: str, data: dict = None) -> bool:
    if not FIREBASE_KEY:
        logger.info(f"[MOCK PUSH] {title}: {body}")
        return True
    try:
        import requests
        payload = {
            "to": token,
            "notification": {"title": title, "body": body, "sound": "default"},
            "data": data or {},
        }
        resp = requests.post(
            "https://fcm.googleapis.com/fcm/send",
            headers={"Authorization": f"key={FIREBASE_KEY}", "Content-Type": "application/json"},
            json=payload,
            timeout=10,
        )
        return resp.status_code == 200
    except Exception as e:
        logger.error(f"Push error: {e}")
        return False


# ─── Email ───────────────────────────────────────────────────────────────────

def send_email(to: str, subject: str, html_body: str) -> bool:
    if not SENDGRID_KEY:
        logger.info(f"[MOCK EMAIL] To {to}: {subject}")
        return True
    try:
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail
        message = Mail(
            from_email="alerts@connectingthedots.gov.in",
            to_emails=to,
            subject=subject,
            html_content=html_body,
        )
        sg = SendGridAPIClient(SENDGRID_KEY)
        sg.send(message)
        return True
    except Exception as e:
        logger.error(f"Email error: {e}")
        return False


# ─── High-level Alert Functions ───────────────────────────────────────────────

def broadcast_missing_child_alert(child: dict) -> dict:
    """Send all alerts when a child is reported missing."""
    results = {}
    name = child.get("name", "Unknown")
    age = child.get("age_at_disappearance", "?")
    location = child.get("last_seen_location", "Unknown location")
    case_id = child.get("case_id", "N/A")
    phone = child.get("guardian_phone", "")

    sms_body = (
        f"MISSING CHILD ALERT\n"
        f"Name: {name} | Age: {age}\n"
        f"Last seen: {location}\n"
        f"Case ID: {case_id}\n"
        f"Call 1098 (Childline) if seen.\n"
        f"App: https://ctd.app/case/{case_id}"
    )

    # Guardian SMS
    if phone:
        results["guardian_sms"] = send_sms(phone, f"Case {case_id} registered. {sms_body}")

    # Police / authorities
    results["police_sms"] = send_sms(
        POLICE_CONTROL_ROOM,
        f"NEW MISSING CHILD CASE\n{sms_body}"
    )

    # Email
    email = child.get("guardian_email", "")
    if email:
        html = _missing_child_email_html(child)
        results["guardian_email"] = send_email(email, f"Missing Child Alert - Case {case_id}", html)

    return results


def send_match_found_alert(child: dict, sighting: dict, confidence: float) -> dict:
    """Alert when a face match is found."""
    results = {}
    name = child.get("name", "Unknown")
    case_id = child.get("case_id", "N/A")
    location = sighting.get("sighting_location", "Unknown")
    phone = child.get("guardian_phone", "")
    pct = int(confidence * 100)

    sms_body = (
        f"POSSIBLE MATCH FOUND\n"
        f"Child: {name} (Case {case_id})\n"
        f"Location: {location}\n"
        f"Match confidence: {pct}%\n"
        f"Please verify immediately.\n"
        f"Call 1098 or visit ctd.app/case/{case_id}"
    )

    if phone:
        results["guardian_sms"] = send_sms(phone, sms_body)

    results["police_sms"] = send_sms(POLICE_CONTROL_ROOM, sms_body)
    return results


def send_sos_alert(lat: float, lon: float, case_id: str, reporter_phone: str) -> dict:
    """Emergency SOS from app."""
    results = {}
    maps_link = f"https://maps.google.com/?q={lat},{lon}"
    sos_message = (
        f"SOS EMERGENCY\n"
        f"Case: {case_id}\n"
        f"Location: {maps_link}\n"
        f"Reported by: {reporter_phone}\n"
        f"RESPOND IMMEDIATELY"
    )
    results["police"] = send_sms(POLICE_CONTROL_ROOM, sos_message)
    results["childline"] = send_sms(CHILDLINE_NUMBER, sos_message)
    return results


# ─── Email Template ───────────────────────────────────────────────────────────

def _missing_child_email_html(child: dict) -> str:
    return f"""
    <html><body style="font-family:Arial;background:#f4f4f4;padding:20px">
    <div style="max-width:600px;margin:auto;background:white;padding:30px;border-radius:8px">
      <div style="background:#e63946;color:white;padding:15px;border-radius:6px;text-align:center">
        <h1 style="margin:0">⚠️ MISSING CHILD ALERT</h1>
      </div>
      <h2>{child.get('name','')}</h2>
      <table style="width:100%;border-collapse:collapse">
        <tr><td style="padding:8px;border:1px solid #ddd"><b>Case ID</b></td>
            <td style="padding:8px;border:1px solid #ddd">{child.get('case_id','')}</td></tr>
        <tr><td style="padding:8px;border:1px solid #ddd"><b>Age</b></td>
            <td style="padding:8px;border:1px solid #ddd">{child.get('age_at_disappearance','')}</td></tr>
        <tr><td style="padding:8px;border:1px solid #ddd"><b>Last Seen</b></td>
            <td style="padding:8px;border:1px solid #ddd">{child.get('last_seen_location','')}</td></tr>
        <tr><td style="padding:8px;border:1px solid #ddd"><b>Missing Since</b></td>
            <td style="padding:8px;border:1px solid #ddd">{child.get('missing_since','')}</td></tr>
      </table>
      <p>{child.get('description','')}</p>
      <p style="color:#666">If you have seen this child, call <b>1098 (Childline)</b> immediately.</p>
      <a href="https://ctd.app/case/{child.get('case_id','')}"
         style="background:#e63946;color:white;padding:12px 24px;text-decoration:none;border-radius:5px">
        View Case Details
      </a>
    </div></body></html>
    """
