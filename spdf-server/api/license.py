"""
License Enforcement API Module

Provides license validation, creation, revocation, and management endpoints.
"""

import secrets
import string
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Optional, List
from collections import defaultdict
import time

from fastapi import APIRouter, HTTPException, Request, Depends, Header
from pydantic import BaseModel, Field, EmailStr
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/license", tags=["license"])

# Rate limiting storage
_rate_limit_store: dict = defaultdict(list)
_failed_attempts: dict = defaultdict(list)

# Rate limiting config
RATE_LIMIT_WINDOW = 60  # seconds
RATE_LIMIT_MAX_REQUESTS = 20
BRUTE_FORCE_WINDOW = 300  # 5 minutes
BRUTE_FORCE_MAX_ATTEMPTS = 5
LOCKOUT_DURATION = 900  # 15 minutes


class LicenseValidateRequest(BaseModel):
    """License validation request."""
    license_key: str = Field(..., pattern=r'^SPDF-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}$')
    device_hash: str = Field(..., min_length=64, max_length=64)
    doc_id: str = Field(..., min_length=1, max_length=256)


class LicenseCreateRequest(BaseModel):
    """License creation request."""
    user_email: EmailStr
    doc_id: str = Field(..., min_length=1, max_length=256)
    max_devices: int = Field(default=2, ge=1, le=10)
    expires_days: Optional[int] = Field(default=None, ge=1, le=3650)
    permissions: Optional[dict] = None


class LicenseRevokeRequest(BaseModel):
    """License revocation request."""
    license_key: str = Field(..., pattern=r'^SPDF-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}$')
    reason: Optional[str] = None


class LicenseResponse(BaseModel):
    """License information response."""
    license_key: str
    user_email: str
    doc_id: str
    max_devices: int
    used_devices: int
    created_at: datetime
    expires_at: Optional[datetime]
    is_active: bool


class KeyResponse(BaseModel):
    """Document key response for decryption."""
    doc_key: str  # Base64 encoded
    public_key: str  # PEM encoded
    permissions: dict


def generate_license_key() -> str:
    """
    Generate a unique license key.
    
    Format: SPDF-XXXX-XXXX-XXXX-XXXX
    """
    chars = string.ascii_uppercase + string.digits
    parts = []
    for _ in range(4):
        part = ''.join(secrets.choice(chars) for _ in range(4))
        parts.append(part)
    return f"SPDF-{'-'.join(parts)}"


def get_client_ip(request: Request) -> str:
    """Get client IP from request."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def check_rate_limit(client_ip: str) -> bool:
    """Check if client is within rate limits."""
    now = time.time()
    window_start = now - RATE_LIMIT_WINDOW
    
    _rate_limit_store[client_ip] = [
        t for t in _rate_limit_store[client_ip] 
        if t > window_start
    ]
    
    if len(_rate_limit_store[client_ip]) >= RATE_LIMIT_MAX_REQUESTS:
        return False
    
    _rate_limit_store[client_ip].append(now)
    return True


def check_brute_force(client_ip: str, license_key: str) -> bool:
    """
    Check for brute force attacks.
    
    Returns True if request should be blocked.
    """
    now = time.time()
    key = f"{client_ip}:{license_key}"
    
    # Check for lockout
    lockout_key = f"lockout:{key}"
    if lockout_key in _failed_attempts:
        lockout_time = _failed_attempts[lockout_key]
        if now < lockout_time:
            return True  # Still locked out
        del _failed_attempts[lockout_key]
    
    # Clean old attempts
    window_start = now - BRUTE_FORCE_WINDOW
    _failed_attempts[key] = [
        t for t in _failed_attempts.get(key, [])
        if t > window_start
    ]
    
    return len(_failed_attempts.get(key, [])) >= BRUTE_FORCE_MAX_ATTEMPTS


def record_failed_attempt(client_ip: str, license_key: str):
    """Record a failed validation attempt."""
    now = time.time()
    key = f"{client_ip}:{license_key}"
    
    if key not in _failed_attempts:
        _failed_attempts[key] = []
    
    _failed_attempts[key].append(now)
    
    # Check if we need to lock out
    if len(_failed_attempts[key]) >= BRUTE_FORCE_MAX_ATTEMPTS:
        lockout_key = f"lockout:{key}"
        _failed_attempts[lockout_key] = now + LOCKOUT_DURATION
        logger.warning(f"Locking out {key} for {LOCKOUT_DURATION}s due to brute force")


def clear_failed_attempts(client_ip: str, license_key: str):
    """Clear failed attempts on successful validation."""
    key = f"{client_ip}:{license_key}"
    if key in _failed_attempts:
        del _failed_attempts[key]


@router.post("/validate")
async def validate_license(
    request: Request,
    data: LicenseValidateRequest
):
    """
    Validate a license and get document decryption key.
    
    This endpoint:
    1. Validates the license key exists and is active
    2. Verifies the device hash is registered or registers it
    3. Checks device limits
    4. Returns the document key if valid
    
    Rate limited to prevent brute force attacks.
    """
    client_ip = get_client_ip(request)
    
    # Rate limiting
    if not check_rate_limit(client_ip):
        raise HTTPException(
            status_code=429, 
            detail="Rate limit exceeded. Please try again later."
        )
    
    # Brute force protection
    if check_brute_force(client_ip, data.license_key):
        raise HTTPException(
            status_code=429,
            detail="Too many failed attempts. Account temporarily locked."
        )
    
    # In production, this would:
    # 1. Query database for license
    # 2. Verify license is active and not expired
    # 3. Check device hash is registered or under limit
    # 4. Get wrapped doc key and unwrap it
    # 5. Return the key
    
    # Placeholder - simulate validation
    # In real implementation, validate against database
    is_valid = data.license_key.startswith("SPDF-")
    
    if not is_valid:
        record_failed_attempt(client_ip, data.license_key)
        raise HTTPException(status_code=403, detail="Invalid license key")
    
    clear_failed_attempts(client_ip, data.license_key)
    
    # Placeholder response
    return {
        "valid": True,
        "doc_id": data.doc_id,
        "permissions": {
            "allow_print": False,
            "allow_copy": False,
            "offline_days": 7
        },
        "device_registered": True,
        "expires_at": None,
        # In production: return actual base64-encoded doc_key
        "doc_key": None,  # Would be filled by actual key lookup
        "public_key": None  # Would be filled by actual key lookup
    }


@router.post("/create")
async def create_license(
    request: Request,
    data: LicenseCreateRequest,
    x_admin_token: str = Header(...)
):
    """
    Create a new license (admin only).
    
    Creates a license binding a user email to a document with
    specified permissions and device limits.
    """
    # TODO: Validate admin token
    
    client_ip = get_client_ip(request)
    if not check_rate_limit(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    # Generate new license key
    license_key = generate_license_key()
    
    # Calculate expiration
    expires_at = None
    if data.expires_days:
        expires_at = datetime.utcnow() + timedelta(days=data.expires_days)
    
    # In production: store in database
    
    return {
        "success": True,
        "license_key": license_key,
        "user_email": data.user_email,
        "doc_id": data.doc_id,
        "max_devices": data.max_devices,
        "expires_at": expires_at.isoformat() if expires_at else None,
        "created_at": datetime.utcnow().isoformat()
    }


@router.post("/revoke")
async def revoke_license(
    request: Request,
    data: LicenseRevokeRequest,
    x_admin_token: str = Header(...)
):
    """
    Revoke a license (admin only).
    
    This invalidates the license and all associated device bindings.
    """
    # TODO: Validate admin token
    
    client_ip = get_client_ip(request)
    if not check_rate_limit(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    # In production: mark license as revoked in database
    
    return {
        "success": True,
        "license_key": data.license_key,
        "revoked_at": datetime.utcnow().isoformat(),
        "reason": data.reason
    }


@router.get("/status/{license_key}")
async def get_license_status(
    license_key: str,
    request: Request
):
    """
    Get license status and information.
    """
    client_ip = get_client_ip(request)
    if not check_rate_limit(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    # Validate format
    import re
    if not re.match(r'^SPDF-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}$', license_key):
        raise HTTPException(status_code=400, detail="Invalid license key format")
    
    # In production: query database
    # Placeholder response
    return {
        "license_key": license_key,
        "status": "active",
        "user_email": "user@example.com",
        "doc_id": "DOC-001",
        "max_devices": 2,
        "used_devices": 1,
        "expires_at": None,
        "created_at": datetime.utcnow().isoformat()
    }


@router.get("/list")
async def list_licenses(
    request: Request,
    doc_id: Optional[str] = None,
    user_email: Optional[str] = None,
    x_admin_token: str = Header(...)
):
    """
    List licenses (admin only).
    
    Optionally filter by document or user.
    """
    # TODO: Validate admin token
    
    client_ip = get_client_ip(request)
    if not check_rate_limit(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    # In production: query database with filters
    return {
        "licenses": [],
        "total": 0,
        "filters": {
            "doc_id": doc_id,
            "user_email": user_email
        }
    }
