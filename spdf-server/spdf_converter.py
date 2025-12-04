"""
SPDF Conversion Module - Server-side PDF to SPDF conversion

This module provides the same functionality as the CLI but for server-side use.
"""

import os
import json
import secrets
from datetime import datetime, timezone
from pathlib import Path

# Import from spdf-format library
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "spdf-format"))

from spdf_format import (
    encrypt_pdf, 
    sign_spdf, 
    write_spdf, 
    generate_k_doc
)

# Import key manager
from utils.key_manager import KeyManager

# Global key manager instance
_key_manager = KeyManager()


def sanitize_pdf(pdf_bytes: bytes) -> bytes:
    """
    Sanitize PDF by removing JavaScript, embedded files, and forms.
    Returns cleaned PDF bytes.
    """
    import fitz  # PyMuPDF
    
    # Open PDF from bytes
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    
    # Remove JavaScript
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
    
    # Remove form fields (flatten)
    for page in doc:
        # Remove annotations that could contain scripts
        annots = page.annots()
        if annots:
            for annot in annots:
                if annot.type[0] in [19, 20]:  # Widget, Screen
                    page.delete_annot(annot)
    
    # Save to bytes
    sanitized = doc.tobytes(garbage=4, deflate=True)
    doc.close()
    
    return sanitized


def convert_pdf_to_spdf(
    pdf_bytes: bytes,
    doc_id: str,
    org_id: str,
    server_url: str,
    title: str = "",
    allow_print: bool = False,
    allow_copy: bool = False,
    max_devices: int = 2,
    watermark_enabled: bool = True,
    watermark_text: str = "{{user_id}} | {{device_id}}"
) -> tuple[bytes, bytes]:
    """
    Convert PDF bytes to SPDF format.
    
    Returns:
        tuple: (spdf_bytes, k_doc_bytes)
    """
    # 1. Sanitize PDF
    sanitized_pdf = sanitize_pdf(pdf_bytes)
    
    # 2. Generate encryption key
    k_doc = generate_k_doc()
    
    # 3. Encrypt PDF content
    encrypted_content = encrypt_pdf(sanitized_pdf, k_doc)
    
    # 4. Build header
    header = {
        "spdf_version": "1.0",
        "doc_id": doc_id,
        "org_id": org_id,
        "title": title or doc_id,
        "server_url": server_url,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "permissions": {
            "allow_print": allow_print,
            "allow_copy": allow_copy,
            "max_devices": max_devices
        },
        "watermark": {
            "enabled": watermark_enabled,
            "text": watermark_text
        }
    }
    
    # 5. Get signing key
    private_key = _key_manager.get_signing_key(org_id)
    
    # 6. Write SPDF to bytes (in-memory)
    import io
    buffer = io.BytesIO()
    
    # Write SPDF structure
    header_json = json.dumps(header).encode('utf-8')
    
    # MAGIC
    buffer.write(b'SPDF')
    # VERSION
    buffer.write(bytes([1]))
    # HEADER_LEN
    buffer.write(len(header_json).to_bytes(4, 'big'))
    # HEADER_JSON
    buffer.write(header_json)
    # CONTENT
    buffer.write(encrypted_content)
    
    # Get data for signing (everything except signature)
    data_to_sign = buffer.getvalue()
    
    # 7. Sign
    signature = sign_spdf(data_to_sign, private_key)
    
    # 8. Append signature
    buffer.write(signature)
    
    spdf_bytes = buffer.getvalue()
    
    return spdf_bytes, k_doc


def get_org_public_key(org_id: str) -> str:
    """Get the public key PEM for an organization."""
    return _key_manager.get_public_key_pem(org_id)
