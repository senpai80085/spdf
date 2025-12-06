"""
SPDF Decryption Module

Provides SPDF file parsing and decryption functionality.
"""

import json
import struct
import hashlib
import logging
from typing import Dict, Tuple, Optional
from dataclasses import dataclass

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.hazmat.primitives import serialization

from .keys import KeyManager, get_key_manager

logger = logging.getLogger(__name__)

# SPDF Format Constants
MAGIC = b"SPDF"
VERSION = 0x01
NONCE_LENGTH = 12
TAG_LENGTH = 16
SIGNATURE_LENGTH = 64
WRAPPED_KEY_LENGTH = 40

# Flag bits
FLAG_DEVICE_BINDING = 0x0001
FLAG_OFFLINE_ALLOWED = 0x0002
FLAG_PRINT_ALLOWED = 0x0004
FLAG_COPY_ALLOWED = 0x0008
FLAG_WATERMARK_ENABLED = 0x0010


class DecryptionError(Exception):
    """Raised when decryption operations fail."""
    pass


class FormatError(Exception):
    """Raised when SPDF format is invalid."""
    pass


class SignatureError(Exception):
    """Raised when signature verification fails."""
    pass


@dataclass
class SpdfHeader:
    """Parsed SPDF header data."""
    spdf_version: str
    doc_id: str
    org_id: str
    title: str
    server_url: str
    created_at: str
    public_key: str
    permissions: Dict
    watermark: Dict
    metadata: Dict


@dataclass
class SpdfFile:
    """Parsed SPDF file structure."""
    version: int
    flags: int
    header: SpdfHeader
    wrapped_key: bytes
    nonce: bytes
    ciphertext: bytes
    auth_tag: bytes
    signature: bytes
    unsigned_data: bytes
    
    @property
    def device_binding_required(self) -> bool:
        return bool(self.flags & FLAG_DEVICE_BINDING)
    
    @property
    def offline_allowed(self) -> bool:
        return bool(self.flags & FLAG_OFFLINE_ALLOWED)
    
    @property
    def print_allowed(self) -> bool:
        return bool(self.flags & FLAG_PRINT_ALLOWED)
    
    @property
    def copy_allowed(self) -> bool:
        return bool(self.flags & FLAG_COPY_ALLOWED)
    
    @property
    def watermark_enabled(self) -> bool:
        return bool(self.flags & FLAG_WATERMARK_ENABLED)


def parse_spdf(data: bytes) -> SpdfFile:
    """
    Parse SPDF file structure.
    
    Args:
        data: Raw SPDF file bytes
        
    Returns:
        SpdfFile instance
        
    Raises:
        FormatError: If file format is invalid
    """
    pos = 0
    
    # Check minimum size
    if len(data) < 11 + WRAPPED_KEY_LENGTH + NONCE_LENGTH + TAG_LENGTH + SIGNATURE_LENGTH:
        raise FormatError("File too short")
    
    # Parse MAGIC (4 bytes)
    if data[pos:pos+4] != MAGIC:
        raise FormatError(f"Invalid magic bytes: expected {MAGIC}, got {data[pos:pos+4]}")
    pos += 4
    
    # Parse VERSION (1 byte)
    version = data[pos]
    if version != VERSION:
        raise FormatError(f"Unsupported version: {version}")
    pos += 1
    
    # Parse FLAGS (2 bytes, big-endian)
    flags = struct.unpack('>H', data[pos:pos+2])[0]
    pos += 2
    
    # Parse HEADER_LEN (4 bytes, big-endian)
    header_len = struct.unpack('>I', data[pos:pos+4])[0]
    pos += 4
    
    # Parse HEADER (JSON)
    if len(data) < pos + header_len:
        raise FormatError("File too short for header")
    
    header_json = data[pos:pos+header_len]
    pos += header_len
    
    try:
        header_dict = json.loads(header_json.decode('utf-8'))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise FormatError(f"Invalid header JSON: {e}")
    
    header = SpdfHeader(
        spdf_version=header_dict.get("spdf_version", "1.0"),
        doc_id=header_dict.get("doc_id", ""),
        org_id=header_dict.get("org_id", ""),
        title=header_dict.get("title", ""),
        server_url=header_dict.get("server_url", ""),
        created_at=header_dict.get("created_at", ""),
        public_key=header_dict.get("public_key", ""),
        permissions=header_dict.get("permissions", {}),
        watermark=header_dict.get("watermark", {}),
        metadata=header_dict.get("metadata", {})
    )
    
    # Parse WRAPPED_KEY (40 bytes)
    if len(data) < pos + WRAPPED_KEY_LENGTH:
        raise FormatError("File too short for wrapped key")
    wrapped_key = data[pos:pos+WRAPPED_KEY_LENGTH]
    pos += WRAPPED_KEY_LENGTH
    
    # Parse NONCE (12 bytes)
    if len(data) < pos + NONCE_LENGTH:
        raise FormatError("File too short for nonce")
    nonce = data[pos:pos+NONCE_LENGTH]
    pos += NONCE_LENGTH
    
    # Signature is last 64 bytes
    if len(data) < pos + TAG_LENGTH + SIGNATURE_LENGTH:
        raise FormatError("File too short for tag and signature")
    
    signature = data[-SIGNATURE_LENGTH:]
    unsigned_data = data[:-SIGNATURE_LENGTH]
    
    # Ciphertext is between nonce and (auth_tag + signature)
    ciphertext_end = len(data) - SIGNATURE_LENGTH - TAG_LENGTH
    if ciphertext_end <= pos:
        raise FormatError("Invalid ciphertext length")
    
    ciphertext = data[pos:ciphertext_end]
    auth_tag = data[ciphertext_end:ciphertext_end+TAG_LENGTH]
    
    return SpdfFile(
        version=version,
        flags=flags,
        header=header,
        wrapped_key=wrapped_key,
        nonce=nonce,
        ciphertext=ciphertext,
        auth_tag=auth_tag,
        signature=signature,
        unsigned_data=unsigned_data
    )


def parse_spdf_file(path: str) -> SpdfFile:
    """Parse SPDF file from path."""
    with open(path, 'rb') as f:
        data = f.read()
    return parse_spdf(data)


def verify_signature(spdf: SpdfFile) -> bool:
    """
    Verify SPDF signature using embedded public key.
    
    Args:
        spdf: Parsed SpdfFile
        
    Returns:
        True if signature is valid
        
    Raises:
        SignatureError: If signature verification fails
    """
    try:
        # Parse public key from header
        pem_data = spdf.header.public_key.encode('utf-8')
        public_key = serialization.load_pem_public_key(pem_data)
        
        if not isinstance(public_key, Ed25519PublicKey):
            raise SignatureError("Invalid public key type - expected Ed25519")
        
        # Hash the unsigned data
        data_hash = hashlib.sha256(spdf.unsigned_data).digest()
        
        # Verify signature
        public_key.verify(spdf.signature, data_hash)
        return True
        
    except Exception as e:
        raise SignatureError(f"Signature verification failed: {e}")


def decrypt_content(spdf: SpdfFile, doc_key: bytes) -> bytes:
    """
    Decrypt SPDF content using document key.
    
    Args:
        spdf: Parsed SpdfFile
        doc_key: 32-byte document encryption key
        
    Returns:
        Decrypted PDF bytes
        
    Raises:
        DecryptionError: If decryption fails
    """
    if len(doc_key) != 32:
        raise DecryptionError("Document key must be 32 bytes")
    
    try:
        aesgcm = AESGCM(doc_key)
        
        # Combine ciphertext and tag
        ciphertext_with_tag = spdf.ciphertext + spdf.auth_tag
        
        # Decrypt
        plaintext = aesgcm.decrypt(spdf.nonce, ciphertext_with_tag, None)
        return plaintext
        
    except Exception as e:
        raise DecryptionError(f"Decryption failed: {e}")


def decrypt_spdf(
    data: bytes,
    key_manager: Optional[KeyManager] = None,
    verify: bool = True
) -> Tuple[bytes, SpdfFile]:
    """
    Parse, verify, and decrypt SPDF data.
    
    Args:
        data: Raw SPDF file bytes
        key_manager: KeyManager for key unwrapping (optional)
        verify: Whether to verify signature
        
    Returns:
        Tuple of (decrypted_pdf_bytes, parsed_spdf_file)
    """
    # Parse file
    spdf = parse_spdf(data)
    
    # Verify signature
    if verify:
        verify_signature(spdf)
    
    # Get key manager
    if key_manager is None:
        key_manager = get_key_manager(spdf.header.org_id)
    
    # Unwrap document key
    doc_key = key_manager.unwrap_key(spdf.wrapped_key)
    
    # Decrypt content
    pdf_bytes = decrypt_content(spdf, doc_key)
    
    return pdf_bytes, spdf


def decrypt_spdf_file(
    input_path: str,
    output_path: str,
    key_manager: Optional[KeyManager] = None,
    verify: bool = True
) -> SpdfFile:
    """
    Decrypt SPDF file to PDF.
    
    Args:
        input_path: Path to SPDF file
        output_path: Path for output PDF
        key_manager: KeyManager instance
        verify: Whether to verify signature
        
    Returns:
        Parsed SpdfFile
    """
    with open(input_path, 'rb') as f:
        data = f.read()
    
    pdf_bytes, spdf = decrypt_spdf(data, key_manager, verify)
    
    with open(output_path, 'wb') as f:
        f.write(pdf_bytes)
    
    return spdf


def get_spdf_info(data: bytes) -> Dict:
    """
    Get metadata from SPDF without decrypting.
    
    Args:
        data: Raw SPDF file bytes
        
    Returns:
        Dictionary with file information
    """
    spdf = parse_spdf(data)
    
    return {
        "version": spdf.version,
        "doc_id": spdf.header.doc_id,
        "org_id": spdf.header.org_id,
        "title": spdf.header.title,
        "server_url": spdf.header.server_url,
        "created_at": spdf.header.created_at,
        "permissions": spdf.header.permissions,
        "watermark": spdf.header.watermark,
        "device_binding_required": spdf.device_binding_required,
        "offline_allowed": spdf.offline_allowed,
        "content_size": len(spdf.ciphertext)
    }
