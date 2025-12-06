"""
Files API Module

Provides SPDF file upload, conversion, and management endpoints.
"""

import os
import logging
from datetime import datetime
from typing import Optional
from pathlib import Path
import tempfile
import shutil

from fastapi import APIRouter, HTTPException, Request, UploadFile, File, Form, Header
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field

from crypto.encrypt import create_spdf, sanitize_pdf
from crypto.decrypt import parse_spdf, get_spdf_info
from crypto.keys import get_key_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/files", tags=["files"])

# Upload settings
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
ALLOWED_EXTENSIONS = {'.pdf'}
UPLOAD_DIR = Path(__file__).parent.parent / "uploads"
SPDF_DIR = Path(__file__).parent.parent / "spdf_files"

# Ensure directories exist
UPLOAD_DIR.mkdir(exist_ok=True)
SPDF_DIR.mkdir(exist_ok=True)


class ConvertRequest(BaseModel):
    """PDF to SPDF conversion request."""
    doc_id: str = Field(..., min_length=1, max_length=256)
    title: Optional[str] = Field(None, max_length=512)
    org_id: str = Field(default="default", max_length=128)
    server_url: str = Field(default="http://localhost:8000")
    allow_print: bool = False
    allow_copy: bool = False
    max_devices: int = Field(default=2, ge=1, le=10)
    offline_days: int = Field(default=0, ge=0, le=365)
    watermark_enabled: bool = True
    watermark_text: str = "{{user_email}} | {{device_id}}"


class FileInfoResponse(BaseModel):
    """SPDF file information."""
    doc_id: str
    title: str
    org_id: str
    created_at: str
    permissions: dict
    file_size: int


def validate_pdf(data: bytes) -> bool:
    """Validate that data is a PDF file."""
    return data[:4] == b'%PDF'


@router.post("/upload")
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    x_admin_token: str = Header(...)
):
    """
    Upload a PDF file for later conversion.
    
    Returns a temporary file ID that can be used with /convert.
    """
    # Validate file extension
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {ALLOWED_EXTENSIONS}"
        )
    
    # Read file with size limit
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size: {MAX_FILE_SIZE // 1024 // 1024}MB"
        )
    
    # Validate PDF magic bytes
    if not validate_pdf(contents):
        raise HTTPException(status_code=400, detail="Invalid PDF file")
    
    # Save to upload directory
    import uuid
    file_id = str(uuid.uuid4())
    upload_path = UPLOAD_DIR / f"{file_id}.pdf"
    
    with open(upload_path, 'wb') as f:
        f.write(contents)
    
    return {
        "success": True,
        "file_id": file_id,
        "filename": file.filename,
        "size": len(contents),
        "uploaded_at": datetime.utcnow().isoformat()
    }


@router.post("/convert")
async def convert_to_spdf(
    request: Request,
    file_id: str = Form(...),
    doc_id: str = Form(...),
    title: Optional[str] = Form(None),
    org_id: str = Form("default"),
    server_url: str = Form("http://localhost:8000"),
    allow_print: bool = Form(False),
    allow_copy: bool = Form(False),
    max_devices: int = Form(2),
    x_admin_token: str = Header(...)
):
    """
    Convert uploaded PDF to SPDF format.
    
    Uses the file_id from a previous upload.
    """
    # Find uploaded file
    upload_path = UPLOAD_DIR / f"{file_id}.pdf"
    if not upload_path.exists():
        raise HTTPException(status_code=404, detail="Upload not found")
    
    # Read PDF
    with open(upload_path, 'rb') as f:
        pdf_bytes = f.read()
    
    # Create SPDF
    try:
        spdf_bytes, wrapped_key = create_spdf(
            pdf_bytes=pdf_bytes,
            doc_id=doc_id,
            org_id=org_id,
            server_url=server_url,
            title=title or doc_id,
            allow_print=allow_print,
            allow_copy=allow_copy,
            max_devices=max_devices
        )
    except Exception as e:
        logger.error(f"Conversion failed: {e}")
        raise HTTPException(status_code=500, detail=f"Conversion failed: {str(e)}")
    
    # Save SPDF file
    spdf_path = SPDF_DIR / f"{doc_id}.spdf"
    with open(spdf_path, 'wb') as f:
        f.write(spdf_bytes)
    
    # Clean up uploaded PDF
    try:
        upload_path.unlink()
    except Exception:
        pass
    
    # In production: store wrapped_key in database
    # For now, just return success
    
    return {
        "success": True,
        "doc_id": doc_id,
        "spdf_size": len(spdf_bytes),
        "spdf_path": str(spdf_path),
        "created_at": datetime.utcnow().isoformat()
    }


@router.post("/convert-direct")
async def convert_direct(
    request: Request,
    file: UploadFile = File(...),
    doc_id: str = Form(...),
    title: Optional[str] = Form(None),
    org_id: str = Form("default"),
    server_url: str = Form("http://localhost:8000"),
    allow_print: bool = Form(False),
    allow_copy: bool = Form(False),
    max_devices: int = Form(2),
    x_admin_token: str = Header(...)
):
    """
    Upload and convert PDF to SPDF in one step.
    
    Returns the SPDF file directly.
    """
    # Read and validate
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large")
    
    if not validate_pdf(contents):
        raise HTTPException(status_code=400, detail="Invalid PDF file")
    
    # Create SPDF
    try:
        spdf_bytes, wrapped_key = create_spdf(
            pdf_bytes=contents,
            doc_id=doc_id,
            org_id=org_id,
            server_url=server_url,
            title=title or doc_id,
            allow_print=allow_print,
            allow_copy=allow_copy,
            max_devices=max_devices
        )
    except Exception as e:
        logger.error(f"Conversion failed: {e}")
        raise HTTPException(status_code=500, detail=f"Conversion failed: {str(e)}")
    
    # Save SPDF file
    spdf_path = SPDF_DIR / f"{doc_id}.spdf"
    with open(spdf_path, 'wb') as f:
        f.write(spdf_bytes)
    
    # Return SPDF file
    return Response(
        content=spdf_bytes,
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{doc_id}.spdf"'
        }
    )


@router.get("/download/{doc_id}")
async def download_spdf(
    doc_id: str,
    request: Request
):
    """
    Download an SPDF file by document ID.
    """
    spdf_path = SPDF_DIR / f"{doc_id}.spdf"
    
    if not spdf_path.exists():
        raise HTTPException(status_code=404, detail="Document not found")
    
    return FileResponse(
        path=spdf_path,
        filename=f"{doc_id}.spdf",
        media_type="application/octet-stream"
    )


@router.get("/info/{doc_id}")
async def get_file_info(
    doc_id: str,
    request: Request
):
    """
    Get SPDF file metadata without decrypting.
    """
    spdf_path = SPDF_DIR / f"{doc_id}.spdf"
    
    if not spdf_path.exists():
        raise HTTPException(status_code=404, detail="Document not found")
    
    with open(spdf_path, 'rb') as f:
        data = f.read()
    
    try:
        info = get_spdf_info(data)
        info['file_size'] = len(data)
        return info
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid SPDF file: {str(e)}")


@router.delete("/{doc_id}")
async def delete_file(
    doc_id: str,
    request: Request,
    x_admin_token: str = Header(...)
):
    """
    Delete an SPDF file (admin only).
    """
    spdf_path = SPDF_DIR / f"{doc_id}.spdf"
    
    if not spdf_path.exists():
        raise HTTPException(status_code=404, detail="Document not found")
    
    try:
        spdf_path.unlink()
        return {
            "success": True,
            "doc_id": doc_id,
            "deleted_at": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Delete failed: {str(e)}")


@router.get("/list")
async def list_files(
    request: Request,
    x_admin_token: str = Header(...)
):
    """
    List all SPDF files (admin only).
    """
    files = []
    
    for spdf_path in SPDF_DIR.glob("*.spdf"):
        try:
            with open(spdf_path, 'rb') as f:
                data = f.read()
            info = get_spdf_info(data)
            info['file_size'] = len(data)
            info['filename'] = spdf_path.name
            files.append(info)
        except Exception:
            continue
    
    return {
        "files": files,
        "total": len(files)
    }
