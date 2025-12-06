"""
SPDF Encryption Module

Provides PDF encryption and SPDF file packaging functionality.
"""

import os
import json
import struct
import hashlib
import logging
from datetime import datetime, timezone
from typing import Dict, Optional, Tuple
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from .keys import KeyManager, get_key_manager

logger = logging.getLogger(__name__)

# SPDF Format Constants
MAGIC = b"SPDF"
VERSION = 0x01
NONCE_LENGTH = 12
TAG_LENGTH = 16
SIGNATURE_LENGTH = 64

# Flag bits
FLAG_DEVICE_BINDING = 0x0001
FLAG_OFFLINE_ALLOWED = 0x0002
FLAG_PRINT_ALLOWED = 0x0004
FLAG_COPY_ALLOWED = 0x0008
FLAG_WATERMARK_ENABLED = 0x0010


class EncryptionError(Exception):
    """Raised when encryption operations fail."""
    pass


def sanitize_pdf(pdf_bytes: bytes) -> bytes:
    """
    Sanitize PDF by removing potentially dangerous content.
    
    Removes:
    - JavaScript
    - Embedded files
    - Form actions
    - Auto-open actions
    """
    try:
        import fitz  # PyMuPDF
        
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        
        # Remove JavaScript and actions from catalog
        if doc.pdf_catalog():
            doc.xref_set_key(doc.pdf_catalog(), "Names", "null")
            doc.xref_set_key(doc.pdf_catalog(), "OpenAction", "null")
            doc.xref_set_key(doc.pdf_catalog(), "AA", "null")
        
        # Remove embedded files
        try:
            if hasattr(doc, 'embfile_count') and doc.embfile_count() > 0:
                for i in range(doc.embfile_count() - 1, -1, -1):
                    doc.embfile_del(i)
        except Exception:
            pass
        
        # Remove potentially dangerous annotations
        for page in doc:
            annots = page.annots()
            if annots:
                for annot in list(annots):
                    if annot.type[0] in [19, 20]:  # Widget, Screen
                        page.delete_annot(annot)
        
        sanitized = doc.tobytes(garbage=4, deflate=True)
        doc.close()
        
        return sanitized
    except ImportError:
        logger.warning("PyMuPDF not installed - skipping PDF sanitization")
        return pdf_bytes
    except Exception as e:
        logger.error(f"PDF sanitization failed: {e}")
        return pdf_bytes


def build_flags(
    device_binding: bool = True,
    offline_allowed: bool = False,
    print_allowed: bool = False,
    copy_allowed: bool = False,
    watermark_enabled: bool = True
) -> int:
    """Build flags integer from permission settings."""
    flags = 0
    if device_binding:
        flags |= FLAG_DEVICE_BINDING
    if offline_allowed:
        flags |= FLAG_OFFLINE_ALLOWED
    if print_allowed:
        flags |= FLAG_PRINT_ALLOWED
    if copy_allowed:
        flags |= FLAG_COPY_ALLOWED
    if watermark_enabled:
        flags |= FLAG_WATERMARK_ENABLED
    return flags


def encrypt_pdf(pdf_bytes: bytes, doc_key: bytes) -> Tuple[bytes, bytes, bytes]:
    """
    Encrypt PDF using AES-256-GCM.
    
    Args:
        pdf_bytes: Sanitized PDF content
        doc_key: 32-byte encryption key
        
    Returns:
        Tuple of (nonce, ciphertext, auth_tag)
    """
    if len(doc_key) != 32:
        raise EncryptionError("Document key must be 32 bytes")
    
    nonce = os.urandom(NONCE_LENGTH)
    aesgcm = AESGCM(doc_key)
    
    # AES-GCM returns ciphertext || tag
    ciphertext_with_tag = aesgcm.encrypt(nonce, pdf_bytes, None)
    
    # Split ciphertext and tag
    ciphertext = ciphertext_with_tag[:-TAG_LENGTH]
    auth_tag = ciphertext_with_tag[-TAG_LENGTH:]
    
    return nonce, ciphertext, auth_tag


def sign_data(data: bytes, key_manager: KeyManager) -> bytes:
    """
    Sign data using Ed25519.
    
    Args:
        data: Data to sign (will be hashed first)
        key_manager: KeyManager instance
        
    Returns:
        64-byte signature
    """
    signing_key = key_manager.get_signing_key()
    data_hash = hashlib.sha256(data).digest()
    signature = signing_key.sign(data_hash)
    return signature


def create_spdf(
    pdf_bytes: bytes,
    doc_id: str,
    org_id: str,
    server_url: str,
    title: str = "",
    allow_print: bool = False,
    allow_copy: bool = False,
    max_devices: int = 2,
    offline_days: int = 0,
    watermark_enabled: bool = True,
    watermark_text: str = "{{user_email}} | {{device_id}}",
    metadata: Optional[Dict] = None,
    key_manager: Optional[KeyManager] = None
) -> Tuple[bytes, bytes]:
    """
    Create a complete SPDF file from PDF bytes.
    
    Args:
        pdf_bytes: Raw PDF content
        doc_id: Unique document identifier
        org_id: Organization identifier
        server_url: Server URL for license validation
        title: Document title
        allow_print: Whether printing is allowed
        allow_copy: Whether copying is allowed
        max_devices: Maximum devices per license
        offline_days: Days document can be viewed offline
        watermark_enabled: Whether to show watermark
        watermark_text: Watermark template
        metadata: Additional metadata
        key_manager: KeyManager instance (creates default if None)
        
    Returns:
        Tuple of (spdf_bytes, wrapped_doc_key)
    """
    if key_manager is None:
        key_manager = get_key_manager(org_id)
    
    # 1. Sanitize PDF
    sanitized = sanitize_pdf(pdf_bytes)
    
    # 2. Generate and wrap document key
    doc_key = key_manager.generate_doc_key()
    wrapped_key = key_manager.wrap_key(doc_key)
    
    # 3. Encrypt PDF
    nonce, ciphertext, auth_tag = encrypt_pdf(sanitized, doc_key)
    
    # 4. Build flags
    flags = build_flags(
        device_binding=True,
        offline_allowed=(offline_days > 0),
        print_allowed=allow_print,
        copy_allowed=allow_copy,
        watermark_enabled=watermark_enabled
    )
    
    # 5. Build header
    header = {
        "spdf_version": "1.0",
        "doc_id": doc_id,
        "org_id": org_id,
        "title": title or doc_id,
        "server_url": server_url,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "public_key": key_manager.get_public_key_pem(),
        "permissions": {
            "allow_print": allow_print,
            "allow_copy": allow_copy,
            "max_devices": max_devices,
            "offline_days": offline_days
        },
        "watermark": {
            "enabled": watermark_enabled,
            "text": watermark_text
        },
        "metadata": metadata or {}
    }
    
    header_json = json.dumps(header, separators=(',', ':')).encode('utf-8')
    header_len = len(header_json)
    
    # 6. Build unsigned portion
    unsigned_data = bytearray()
    unsigned_data.extend(MAGIC)                           # 4 bytes
    unsigned_data.append(VERSION)                         # 1 byte
    unsigned_data.extend(struct.pack('>H', flags))        # 2 bytes
    unsigned_data.extend(struct.pack('>I', header_len))   # 4 bytes
    unsigned_data.extend(header_json)                     # variable
    unsigned_data.extend(wrapped_key)                     # 40 bytes
    unsigned_data.extend(nonce)                           # 12 bytes
    unsigned_data.extend(ciphertext)                      # variable
    unsigned_data.extend(auth_tag)                        # 16 bytes
    
    # 7. Sign
    signature = sign_data(bytes(unsigned_data), key_manager)
    
    # 8. Build complete file
    spdf_bytes = bytes(unsigned_data) + signature
    
    logger.info(f"Created SPDF: doc_id={doc_id}, size={len(spdf_bytes)}")
    
    return spdf_bytes, wrapped_key


def create_spdf_file(
    input_path: str,
    output_path: str,
    doc_id: str,
    org_id: str,
    server_url: str,
    **kwargs
) -> bytes:
    """
    Create SPDF file from PDF file.
    
    Args:
        input_path: Path to input PDF
        output_path: Path for output SPDF
        doc_id: Document ID
        org_id: Organization ID
        server_url: Server URL
        **kwargs: Additional arguments passed to create_spdf
        
    Returns:
        Wrapped document key
    """
    with open(input_path, 'rb') as f:
        pdf_bytes = f.read()
    
    spdf_bytes, wrapped_key = create_spdf(
        pdf_bytes=pdf_bytes,
        doc_id=doc_id,
        org_id=org_id,
        server_url=server_url,
        **kwargs
    )
    
    with open(output_path, 'wb') as f:
        f.write(spdf_bytes)
    
    return wrapped_key
