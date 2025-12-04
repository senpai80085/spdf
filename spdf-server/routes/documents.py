"""
Document management routes
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
import sys
import os
from pathlib import Path
from datetime import datetime

# Add spdf-format to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'spdf-format'))
from spdf_format import read_spdf

from database import get_db
from models import User, Document, DocumentKey, License
from routes.auth import get_current_user
from routes.keys import encrypt_k_doc
from config import UPLOAD_DIR

router = APIRouter(prefix="/docs", tags=["documents"])


class DocumentInfo(BaseModel):
    doc_id: str
    title: str
    created_at: datetime


@router.get("/{doc_id}/download")
def download_document(
    doc_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Download SPDF file (requires valid license)."""
    # Find document
    document = db.query(Document).filter(Document.doc_id == doc_id).first()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
    
    # Check license
    license = db.query(License).filter(
        License.user_id == current_user.id,
        License.doc_id == doc_id
    ).first()
    
    if not license:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No license for this document",
        )
    
    # Check file exists
    if not os.path.exists(document.spdf_path):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="SPDF file not found on server",
        )
    
    return FileResponse(
        document.spdf_path,
        media_type="application/octet-stream",
        filename=f"{doc_id}.spdf"
    )


@router.post("/upload")
def upload_document(
    file: UploadFile = File(...),
    doc_id: str = None,
    title: str = None,
    org_id: str = "ORG-1",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload SPDF file (admin only).
    File should already be converted to .spdf format.
    """
    if not file.filename.endswith('.spdf'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only .spdf files are allowed",
        )
    
    # Auto-generate doc_id if not provided
    if not doc_id:
        doc_id = f"DOC-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    
    if not title:
        title = file.filename.replace('.spdf', '')
    
    # Save file
    file_path = UPLOAD_DIR / f"{doc_id}.spdf"
    key_path = UPLOAD_DIR / f"{doc_id}.spdf.key"
    
    with open(file_path, 'wb') as f:
        content = file.file.read()
        f.write(content)
    
    # Parse SPDF to validate
    try:
        header, _, _ = read_spdf(str(file_path))
    except Exception as e:
        os.remove(file_path)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid SPDF file: {str(e)}",
        )
    
    # Load K_doc from .key file (should be uploaded alongside)
    # In production, this would come from secure source
    if not key_path.exists():
        # For testing, look for uploaded .key file
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing .key file for document",
        )
    
    with open(key_path, 'rb') as f:
        k_doc = f.read()
    
    if len(k_doc) != 32:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid K_doc length",
        )
    
    # Encrypt K_doc with K_master
    k_doc_encrypted = encrypt_k_doc(k_doc)
    
    # Create document record
    document = Document(
        org_id=org_id,
        doc_id=doc_id,
        title=title,
        spdf_path=str(file_path),
    )
    db.add(document)
    
    # Store encrypted K_doc
    doc_key = DocumentKey(
        doc_id=doc_id,
        k_doc_encrypted=k_doc_encrypted,
    )
    db.add(doc_key)
    
    db.commit()
    db.refresh(document)
    
    return {
        "message": "Document uploaded successfully",
        "doc_id": doc_id,
        "title": title,
        "path": str(file_path)
    }


@router.get("/list", response_model=list[DocumentInfo])
def list_documents(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all documents the user has licenses for."""
    licenses = db.query(License).filter(License.user_id == current_user.id).all()
    
    documents = []
    for license in licenses:
        doc = db.query(Document).filter(Document.doc_id == license.doc_id).first()
        if doc:
            documents.append(DocumentInfo(
                doc_id=doc.doc_id,
                title=doc.title,
                created_at=doc.created_at
            ))
    
    return documents
