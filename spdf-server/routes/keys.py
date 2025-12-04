"""
Key distribution routes
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import os
import base64

from database import get_db
from models import User, Device, License, DocumentKey, Document
from routes.auth import get_current_user
from config import K_MASTER

router = APIRouter(prefix="/keys", tags=["keys"])


class KeyRequest(BaseModel):
    doc_id: str
    device_id: str
    device_name: str


class KeyResponse(BaseModel):
    k_doc: str  # base64 encoded
    permissions: dict
    watermark_data: dict


def encrypt_k_doc(k_doc: bytes) -> bytes:
    """Encrypt K_doc using K_master."""
    nonce = os.urandom(12)
    aesgcm = AESGCM(K_MASTER)
    ciphertext = aesgcm.encrypt(nonce, k_doc, None)
    return nonce + ciphertext


def decrypt_k_doc(encrypted: bytes) -> bytes:
    """Decrypt K_doc using K_master."""
    nonce = encrypted[:12]
    ciphertext = encrypted[12:]
    aesgcm = AESGCM(K_MASTER)
    k_doc = aesgcm.decrypt(nonce, ciphertext, None)
    return k_doc


@router.post("/get", response_model=KeyResponse)
def get_key(
    request: KeyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get decryption key for a document.
    - Checks license
    - Registers/updates device
    - Returns K_doc and permissions
    """
    # Find document
    document = db.query(Document).filter(Document.doc_id == request.doc_id).first()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
    
    # Check license
    license = db.query(License).filter(
        License.user_id == current_user.id,
        License.doc_id == request.doc_id
    ).first()
    
    if not license:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No license for this document",
        )
    
    # Check expiration
    if license.expires_at and license.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="License expired",
        )
    
    # Check or register device
    device = db.query(Device).filter(Device.device_id == request.device_id).first()
    
    if not device:
        # New device - check max_devices
        user_device_count = db.query(Device).filter(Device.user_id == current_user.id).count()
        
        if user_device_count >= license.max_devices:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Maximum devices limit reached ({license.max_devices})",
            )
        
        # Register new device
        device = Device(
            user_id=current_user.id,
            device_id=request.device_id,
            device_name=request.device_name,
        )
        db.add(device)
        db.commit()
        db.refresh(device)
    else:
        # Update last_seen
        device.last_seen = datetime.utcnow()
        db.commit()
    
    # Get K_doc
    doc_key = db.query(DocumentKey).filter(DocumentKey.doc_id == request.doc_id).first()
    if not doc_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Document key not found",
        )
    
    # Decrypt K_doc
    try:
        k_doc = decrypt_k_doc(doc_key.k_doc_encrypted)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to decrypt document key: {str(e)}",
        )
    
    # Get permissions from document (you'd load from SPDF header in real scenario)
    # For now, use license max_devices
    permissions = {
        "allow_print": False,
        "allow_copy": False,
        "max_devices": license.max_devices
    }
    
    # Watermark data
    watermark_data = {
        "user_id": current_user.email,
        "device_id": request.device_id
    }
    
    return KeyResponse(
        k_doc=base64.b64encode(k_doc).decode('utf-8'),
        permissions=permissions,
        watermark_data=watermark_data
    )
