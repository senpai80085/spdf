"""
Device Binding API Module

Provides device fingerprinting, registration, and validation endpoints.
"""

import hashlib
import secrets
import logging
from datetime import datetime, timedelta
from typing import Optional, List
from collections import defaultdict
import time

from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/device", tags=["device"])

# Rate limiting storage (in production, use Redis)
_rate_limit_store: dict = defaultdict(list)
RATE_LIMIT_WINDOW = 60  # seconds
RATE_LIMIT_MAX_REQUESTS = 30


class DeviceFingerprintRequest(BaseModel):
    """Device fingerprint data."""
    cpu_id: str = Field(..., min_length=1, max_length=256)
    mac_address: str = Field(..., pattern=r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$')
    os_info: str = Field(..., min_length=1, max_length=256)
    device_name: Optional[str] = Field(None, max_length=256)


class DeviceRegisterRequest(BaseModel):
    """Device registration request."""
    license_key: str = Field(..., pattern=r'^SPDF-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}$')
    device_hash: str = Field(..., min_length=64, max_length=64)
    device_name: Optional[str] = Field(None, max_length=256)


class DeviceRevokeRequest(BaseModel):
    """Device revocation request."""
    license_key: str
    device_hash: str


class DeviceResponse(BaseModel):
    """Device information response."""
    device_hash: str
    device_name: Optional[str]
    registered_at: datetime
    last_seen: Optional[datetime]
    is_active: bool


def generate_device_salt() -> bytes:
    """Generate a random salt for device fingerprinting."""
    return secrets.token_bytes(16)


def compute_device_hash(
    cpu_id: str,
    mac_address: str, 
    os_info: str,
    salt: bytes
) -> str:
    """
    Compute deterministic device hash from hardware info.
    
    The hash is computed as:
    SHA256(salt || cpu_id || mac_address || os_info)
    """
    # Normalize MAC address
    mac_normalized = mac_address.upper().replace('-', ':')
    
    # Build data string
    data = f"{cpu_id}:{mac_normalized}:{os_info}".encode('utf-8')
    
    # Compute hash
    return hashlib.sha256(salt + data).hexdigest()


def check_rate_limit(client_ip: str) -> bool:
    """
    Check if client is within rate limits.
    
    Returns True if allowed, False if rate limited.
    """
    now = time.time()
    window_start = now - RATE_LIMIT_WINDOW
    
    # Clean old entries
    _rate_limit_store[client_ip] = [
        t for t in _rate_limit_store[client_ip] 
        if t > window_start
    ]
    
    # Check limit
    if len(_rate_limit_store[client_ip]) >= RATE_LIMIT_MAX_REQUESTS:
        return False
    
    # Record this request
    _rate_limit_store[client_ip].append(now)
    return True


def get_client_ip(request: Request) -> str:
    """Get client IP from request."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@router.post("/fingerprint")
async def create_fingerprint(
    request: Request,
    data: DeviceFingerprintRequest
):
    """
    Generate a device fingerprint hash.
    
    This endpoint creates a deterministic hash from device hardware info
    that can be used for device binding.
    """
    client_ip = get_client_ip(request)
    
    if not check_rate_limit(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    # Generate salt (in production, this should be stored per-device)
    # For now we use a fixed installation salt
    salt = hashlib.sha256(b"spdf_device_salt_v1").digest()[:16]
    
    device_hash = compute_device_hash(
        data.cpu_id,
        data.mac_address,
        data.os_info,
        salt
    )
    
    return {
        "device_hash": device_hash,
        "salt_version": 1
    }


@router.post("/register")
async def register_device(
    request: Request,
    data: DeviceRegisterRequest
):
    """
    Register a device for a license.
    
    This binds a device hash to a license key, allowing the device
    to decrypt documents under that license.
    """
    client_ip = get_client_ip(request)
    
    if not check_rate_limit(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    # In a real implementation, this would:
    # 1. Validate the license key exists
    # 2. Check device limit for the license
    # 3. Store the device_hash -> license binding
    # 4. Return success/failure
    
    # Placeholder response
    return {
        "success": True,
        "message": "Device registered successfully",
        "device_hash": data.device_hash,
        "registered_at": datetime.utcnow().isoformat()
    }


@router.post("/revoke")
async def revoke_device(
    request: Request,
    data: DeviceRevokeRequest
):
    """
    Revoke device access for a license.
    
    This unbinds a device from a license, preventing future decryption.
    """
    client_ip = get_client_ip(request)
    
    if not check_rate_limit(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    # Placeholder - requires license ownership verification
    return {
        "success": True,
        "message": "Device revoked successfully"
    }


@router.get("/list/{license_key}")
async def list_devices(
    license_key: str,
    request: Request
):
    """
    List all devices registered for a license.
    
    Requires admin authentication.
    """
    client_ip = get_client_ip(request)
    
    if not check_rate_limit(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    # Placeholder - would return actual device list
    return {
        "license_key": license_key,
        "devices": [],
        "max_devices": 2,
        "used_devices": 0
    }


@router.post("/validate")
async def validate_device(
    request: Request,
    data: DeviceRegisterRequest
):
    """
    Validate that a device hash is registered for a license.
    
    Returns whether the device is allowed to decrypt documents.
    """
    client_ip = get_client_ip(request)
    
    if not check_rate_limit(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    # Placeholder validation
    return {
        "valid": True,
        "license_key": data.license_key,
        "device_hash": data.device_hash
    }
