"""
License Key Authentication Route
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime, timedelta

from database import get_db
from models import User, License
from routes.auth import create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES

router = APIRouter(prefix="/auth", tags=["auth"])


class LicenseKeyRequest(BaseModel):
    license_key: str


class LicenseKeyResponse(BaseModel):
    access_token: str
    token_type: str
    user_email: str
    doc_id: str


@router.post("/login-with-key", response_model=LicenseKeyResponse)
def login_with_license_key(request: LicenseKeyRequest, db: Session = Depends(get_db)):
    """
    Authenticate using a license key.
    Returns JWT token with embedded user_id and doc_id.
    """
    # Find license by key
    license_obj = db.query(License).filter(License.license_key == request.license_key).first()
    
    if not license_obj:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid license key",
        )
    
    # Check if license is expired
    if license_obj.expires_at and license_obj.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="License has expired",
        )
    
    # Get user
    user = db.query(User).filter(User.id == license_obj.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    
    # Create access token with embedded license info
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": user.email,
            "doc_id": license_obj.doc_id,
            "license_id": license_obj.id
        },
        expires_delta=access_token_expires
    )
    
    return LicenseKeyResponse(
        access_token=access_token,
        token_type="bearer",
        user_email=user.email,
        doc_id=license_obj.doc_id
    )
