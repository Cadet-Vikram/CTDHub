"""
Aadhaar-based Verification
Uses UIDAI sandbox API for verification.
In production: integrate with UIDAI e-KYC API.
"""
import hashlib
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()
logger = logging.getLogger(__name__)


class AadhaarVerifyRequest(BaseModel):
    aadhaar_number: str
    name: str
    dob: str  # DD/MM/YYYY


@router.post("/verify")
async def verify_aadhaar(req: AadhaarVerifyRequest):
    """
    Verify Aadhaar details.
    Production: calls UIDAI Auth API with OTP.
    Sandbox: returns mock verification.
    """
    if len(req.aadhaar_number.replace(" ", "")) != 12:
        raise HTTPException(400, "Invalid Aadhaar number format")

    aadhaar_clean = req.aadhaar_number.replace(" ", "")
    hashed = hashlib.sha256(aadhaar_clean.encode()).hexdigest()

    # SANDBOX MOCK - replace with real UIDAI call in production
    logger.info(f"Aadhaar verification attempted for hash: {hashed[:8]}...")
    return {
        "verified": True,
        "aadhaar_hash": hashed,
        "name_match": True,
        "dob_match": True,
        "note": "Sandbox mode - real UIDAI API required in production",
    }


@router.post("/hash")
async def hash_aadhaar(req: AadhaarVerifyRequest):
    """Return SHA-256 hash of Aadhaar for safe storage."""
    clean = req.aadhaar_number.replace(" ", "")
    return {"hash": hashlib.sha256(clean.encode()).hexdigest()}
