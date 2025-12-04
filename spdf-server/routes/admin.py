"""
Admin API Routes - Document, User, and License Management
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime
import os
import base64

from database import get_db
from models import User, Document, DocumentKey, License, Device
from routes.auth import get_current_user, get_password_hash
from config import UPLOAD_DIR, K_MASTER
from spdf_converter import convert_pdf_to_spdf, get_org_public_key

# Encryption helpers
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

router = APIRouter(prefix="/admin", tags=["admin"])


def encrypt_k_doc(k_doc: bytes) -> bytes:
    """Encrypt K_doc with K_master."""
    aesgcm = AESGCM(K_MASTER)
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, k_doc, None)
    return nonce + ciphertext


# ============ DOCUMENT MANAGEMENT ============

@router.post("/convert")
async def convert_pdf(
    file: UploadFile = File(...),
    doc_id: str = Form(...),
    title: str = Form(""),
    org_id: str = Form("ORG-1"),
    allow_print: bool = Form(False),
    allow_copy: bool = Form(False),
    max_devices: int = Form(2),
    watermark_enabled: bool = Form(True),
    watermark_text: str = Form("{{user_id}} | {{device_id}}"),
    server_url: str = Form("http://localhost:8000"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Convert uploaded PDF to SPDF and store it.
    This replaces the CLI workflow entirely.
    """
    # Check if doc_id already exists
    existing = db.query(Document).filter(Document.doc_id == doc_id).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Document {doc_id} already exists")
    
    # Read PDF content
    pdf_bytes = await file.read()
    
    if not pdf_bytes.startswith(b'%PDF'):
        raise HTTPException(status_code=400, detail="Invalid PDF file")
    
    try:
        # Convert PDF to SPDF
        spdf_bytes, k_doc = convert_pdf_to_spdf(
            pdf_bytes=pdf_bytes,
            doc_id=doc_id,
            org_id=org_id,
            server_url=server_url,
            title=title or doc_id,
            allow_print=allow_print,
            allow_copy=allow_copy,
            max_devices=max_devices,
            watermark_enabled=watermark_enabled,
            watermark_text=watermark_text
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Conversion failed: {str(e)}")
    
    # Save SPDF file
    UPLOAD_DIR.mkdir(exist_ok=True)
    spdf_path = UPLOAD_DIR / f"{doc_id}.spdf"
    spdf_path.write_bytes(spdf_bytes)
    
    # Encrypt and store K_doc
    k_doc_encrypted = encrypt_k_doc(k_doc)
    
    # Create database entries
    document = Document(
        doc_id=doc_id,
        title=title or doc_id,
        org_id=org_id,
        spdf_path=str(spdf_path),
        created_by=current_user.id
    )
    db.add(document)
    db.flush()
    
    doc_key = DocumentKey(
        doc_id=doc_id,
        k_doc_encrypted=k_doc_encrypted
    )
    db.add(doc_key)
    db.commit()
    
    return {
        "success": True,
        "doc_id": doc_id,
        "title": title or doc_id,
        "message": "PDF converted to SPDF successfully"
    }


@router.get("/documents")
async def list_all_documents(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all documents (admin view)."""
    documents = db.query(Document).all()
    result = []
    for doc in documents:
        # Get document key info
        doc_key = db.query(DocumentKey).filter(DocumentKey.doc_id == doc.doc_id).first()
        
        result.append({
            "id": doc.id,
            "doc_id": doc.doc_id,
            "title": doc.title,
            "org_id": doc.org_id,
            "has_key": doc_key is not None,
            "created_at": doc.created_at.isoformat() if doc.created_at else None
        })
    return result


@router.delete("/documents/{doc_id}")
async def delete_document(
    doc_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a document and its associated data."""
    document = db.query(Document).filter(Document.doc_id == doc_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Delete file
    if os.path.exists(document.spdf_path):
        os.remove(document.spdf_path)
    
    # Delete related records
    db.query(DocumentKey).filter(DocumentKey.doc_id == doc_id).delete()
    db.query(License).filter(License.doc_id == doc_id).delete()
    db.delete(document)
    db.commit()
    
    return {"success": True, "message": f"Document {doc_id} deleted"}


@router.post("/documents/{doc_id}/generate-key")
async def generate_document_key(
    doc_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate or regenerate encryption key for a document."""
    import secrets
    
    # Check if document exists
    document = db.query(Document).filter(Document.doc_id == doc_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Generate new K_doc
    k_doc = secrets.token_bytes(32)  # 256-bit key
    k_doc_encrypted = encrypt_k_doc(k_doc)
    
    # Check if key already exists
    existing_key = db.query(DocumentKey).filter(DocumentKey.doc_id == doc_id).first()
    
    if existing_key:
        # Update existing key
        existing_key.k_doc_encrypted = k_doc_encrypted
    else:
        # Create new key
        doc_key = DocumentKey(
            doc_id=doc_id,
            k_doc_encrypted=k_doc_encrypted
        )
        db.add(doc_key)
    
    db.commit()
    
    return {
        "success": True,
        "message": f"Encryption key {'regenerated' if existing_key else 'generated'} for {doc_id}"
    }


@router.get("/documents/{doc_id}/download")
async def download_spdf(
    doc_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Download SPDF file."""
    document = db.query(Document).filter(Document.doc_id == doc_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return FileResponse(
        document.spdf_path,
        filename=f"{doc_id}.spdf",
        media_type="application/octet-stream"
    )


# ============ USER MANAGEMENT ============

@router.get("/users")
async def list_users(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all users."""
    users = db.query(User).all()
    return [
        {
            "id": user.id,
            "email": user.email,
            "org_id": user.org_id,
            "created_at": user.created_at.isoformat() if user.created_at else None
        }
        for user in users
    ]


@router.post("/users")
async def create_user(
    email: str = Form(...),
    password: str = Form(...),
    org_id: str = Form("ORG-1"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new user."""
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user = User(
        email=email,
        password_hash=get_password_hash(password),
        org_id=org_id
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return {"success": True, "user_id": user.id, "email": email}


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a user and their devices/licenses."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    
    # Delete related records
    db.query(Device).filter(Device.user_id == user_id).delete()
    db.query(License).filter(License.user_id == user_id).delete()
    db.delete(user)
    db.commit()
    
    return {"success": True, "message": f"User {user.email} deleted"}


@router.get("/users/{user_id}/devices")
async def list_user_devices(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List devices registered to a user."""
    devices = db.query(Device).filter(Device.user_id == user_id).all()
    return [
        {
            "id": device.id,
            "device_id": device.device_id,
            "device_name": device.device_name,
            "registered_at": device.registered_at.isoformat() if device.registered_at else None
        }
        for device in devices
    ]


# ============ LICENSE MANAGEMENT ============

@router.get("/licenses")
async def list_all_licenses(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all licenses."""
    licenses = db.query(License).all()
    result = []
    for lic in licenses:
        user = db.query(User).filter(User.id == lic.user_id).first()
        result.append({
            "id": lic.id,
            "user_email": user.email if user else "Unknown",
            "doc_id": lic.doc_id,
            "license_key": lic.license_key,  # Include license key
            "max_devices": lic.max_devices,
            "expires_at": lic.expires_at.isoformat() if lic.expires_at else None
        })
    return result


@router.post("/licenses")
async def create_license(
    user_id: int = Form(...),
    doc_id: str = Form(...),
    max_devices: int = Form(2),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a license for a user to access a document."""
    from models import generate_license_key
    
    # Validate user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Validate document exists
    document = db.query(Document).filter(Document.doc_id == doc_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Check for existing license
    existing = db.query(License).filter(
        License.user_id == user_id,
        License.doc_id == doc_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="License already exists")
    
    # Generate unique license key
    license_key = generate_license_key()
    while db.query(License).filter(License.license_key == license_key).first():
        license_key = generate_license_key()  # Ensure uniqueness
    
    license_obj = License(
        user_id=user_id,
        doc_id=doc_id,
        license_key=license_key,
        max_devices=max_devices
    )
    db.add(license_obj)
    db.commit()
    db.refresh(license_obj)
    
    return {
        "success": True,
        "message": f"License created for {user.email} → {doc_id}",
        "license_key": license_key  # Return key to admin
    }


@router.delete("/licenses/{license_id}")
async def revoke_license(
    license_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Revoke a license."""
    license_obj = db.query(License).filter(License.id == license_id).first()
    if not license_obj:
        raise HTTPException(status_code=404, detail="License not found")
    
    db.delete(license_obj)
    db.commit()
    
    return {"success": True, "message": "License revoked"}


# ============ STATS ============

@router.get("/stats")
async def get_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get dashboard statistics."""
    return {
        "total_documents": db.query(Document).count(),
        "total_users": db.query(User).count(),
        "total_licenses": db.query(License).count(),
        "total_devices": db.query(Device).count()
    }
